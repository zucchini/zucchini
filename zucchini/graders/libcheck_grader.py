import os
import re
import shlex
import tempfile
from fractions import Fraction

from ..submission import BrokenSubmissionError
from ..utils import run_process, PIPE, STDOUT, TimeoutExpired
from ..grades import PartGrade
from . import ThreadedGrader, Part

"""
Grade a native C assignment using Check, a C unit testing framework.
"""


class LibcheckTest(Part):
    __slots__ = ('name')

    REGEX_SUMMARY = re.compile(r'\d+%:\s+Checks:\s+(?P<total>\d+),\s+'
                               r'Failures:\s+(?P<failures>\d+),\s+'
                               r'Errors:\s+(?P<errors>\d+)')

    def __init__(self, name, disable_valgrind=False, valgrind_deduction=None):
        self.name = name
        self.disable_valgrind = disable_valgrind
        self.valgrind_deduction = Fraction(valgrind_deduction) \
            if valgrind_deduction is not None else None

    def description(self):
        return self.name

    @staticmethod
    def format_cmd(cmd, **kwargs):
        return [arg.format(**kwargs) for arg in cmd]

    @staticmethod
    def test_error_grade(message):
        return PartGrade(Fraction(0), deductions=('error',), log=message)

    def grade(self, path, grader):
        """Grade a single libcheck test"""

        grade = PartGrade(Fraction(1), deductions=[], log='')

        logfile_fp, logfile_path = tempfile.mkstemp(prefix='log-', dir=path)
        # Don't leak fds
        os.close(logfile_fp)
        logfile_basename = os.path.basename(logfile_path)

        run_cmd = self.format_cmd(grader.run_cmd, testcase=self.name,
                                  logfile=logfile_basename)
        process = run_process(run_cmd,
                              env={'CK_DEFAULT_TIMEOUT':
                                   str(grader.test_timeout)},
                              cwd=path, stdout=PIPE, stderr=STDOUT)

        if process.returncode != 0:
            return self.test_error_grade('tester exited with {} != 0:\n{}'
                                         .format(process.returncode,
                                                 process.stdout.decode()
                                                 if process.stdout is not None
                                                 else '(no output)'))
        try:
            # NOTE: drop any non-UTF8 characters (e.g. if a string is not
            # null-terminated)
            with open(logfile_path, 'r', errors='ignore') as logfile:
                logfile_contents = logfile.read()
                grade.log += logfile_contents

                summary = logfile_contents.splitlines()[-1]
                match = self.REGEX_SUMMARY.match(summary)
        except IOError as err:
            return self.test_error_grade('could not open log file: {}'
                                         .format(os.strerror(err.errno)))

        total = int(match.group('total'))
        failed = int(match.group('errors')) + int(match.group('failures'))
        grade.score *= Fraction(total - failed, total)

        if grader.valgrind_cmd is None or self.disable_valgrind:
            return grade

        grade.log += '\nValgrind\n--------\n'

        if grade.score < 1:
            valgrind_deduct = False
            grade.log += 'failed this test, so skipping valgrind...\n'
        else:
            # When running valgrind, we need to set CK_FORK=no, else
            # we're gonna get a ton of bogus reported memory leaks.
            # However, CK_FORK=no will break libcheck timeouts, so make
            # sure to handle timeouts here with subprocess
            try:
                valgrind_cmd = self.format_cmd(grader.valgrind_cmd,
                                               testcase=self.name,
                                               logfile=logfile_basename)
                valgrind_process = run_process(valgrind_cmd,
                                               stdout=PIPE,
                                               stderr=STDOUT,
                                               env={'CK_FORK': 'no'},
                                               cwd=path,
                                               timeout=grader.valgrind_timeout)
            except TimeoutExpired:
                grade.log += ('valgrind timed out after {} seconds, deducting '
                              'full valgrind penalty...\n').format(
                                  grader.valgrind_timeout)
                valgrind_deduct = True
            else:
                if valgrind_process.stdout:
                    grade.log += valgrind_process.stdout.decode()
                else:
                    grade.log += '(no output)'
                valgrind_deduct = valgrind_process.returncode != 0

        if valgrind_deduct:
            deduction = self.valgrind_deduction \
                if self.valgrind_deduction is not None \
                else grader.valgrind_deduction
            grade.deductions.append('valgrind')
            grade.score *= 1 - deduction

        return grade


class LibcheckGrader(ThreadedGrader):
    DEFAULT_BUILD_TIMEOUT = 15
    DEFAULT_TEST_TIMEOUT = 5
    DEFAULT_VALGRIND_TIMEOUT = 30

    def __init__(self, build_cmd, run_cmd, valgrind_cmd=None,
                 valgrind_deduction=None, build_timeout=None,
                 test_timeout=None, valgrind_timeout=None,
                 num_threads=None):
        super(LibcheckGrader, self).__init__(num_threads)

        self.build_cmd = shlex.split(build_cmd)
        self.run_cmd = shlex.split(run_cmd)

        self.valgrind_cmd = None \
            if valgrind_cmd is None else shlex.split(valgrind_cmd)
        self.valgrind_deduction = Fraction(1) \
            if valgrind_deduction is None else Fraction(valgrind_deduction)
        self.build_timeout = self.DEFAULT_BUILD_TIMEOUT \
            if build_timeout is None else build_timeout
        self.test_timeout = self.DEFAULT_TEST_TIMEOUT \
            if test_timeout is None else test_timeout
        self.valgrind_timeout = self.DEFAULT_VALGRIND_TIMEOUT \
            if valgrind_timeout is None else valgrind_timeout

    def list_prerequisites(self):
        return ['build-essential', 'check', 'valgrind', 'pkg-config']

    def grade_part(self, part, path, submission):
        return part.grade(path, self)

    def part_from_config_dict(self, config_dict):
        return LibcheckTest.from_config_dict(config_dict)

    def grade(self, submission, path, parts):
        try:
            process = run_process(self.build_cmd, cwd=path,
                                  timeout=self.build_timeout,
                                  stdout=PIPE,
                                  stderr=STDOUT)
        except TimeoutExpired:
            raise BrokenSubmissionError('timeout of {} seconds expired for '
                                        'build command'.format(self.timeout))

        if process.returncode != 0:
            raise BrokenSubmissionError(
                'build command exited with nonzero exit code {}'
                .format(process.returncode),
                verbose=process.stdout.decode() if process.stdout else None)

        return super(LibcheckGrader, self).grade(submission, path, parts)
