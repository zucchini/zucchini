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

    def __init__(self, name):
        self.name = name

    def description(self):
        return self.name

    @staticmethod
    def format_cmd(cmd, **kwargs):
        return [arg.format(**kwargs) for arg in cmd]

    @staticmethod
    def test_error_grade(message):
        return PartGrade(Fraction(0), deductions=('error'), log=message)

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
                              env={'CK_DEFAULT_TIMEOUT': str(grader.timeout)},
                              cwd=path, stdout=PIPE, stderr=STDOUT)

        if process.returncode != 0:
            return self.test_error_grade('tester exited with {} != 0'
                                         .format(process.returncode))
        try:
            with open(logfile_path, 'r') as logfile:
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
                                               timeout=grader.timeout)
            except TimeoutExpired:
                grade.log += 'valgrind timed out, deducting full valgrind ' \
                             'penalty...\n'
                valgrind_deduct = True
            else:
                if valgrind_process.stdout:
                    grade.log += valgrind_process.stdout.decode()
                else:
                    grade.log += '(no output)'
                valgrind_deduct = valgrind_process.returncode != 0

        if valgrind_deduct:
            grade.deductions.append('valgrind')
            grade.score *= 1 - grader.valgrind_deduction

        return grade


class LibcheckGrader(ThreadedGrader):
    DEFAULT_TIMEOUT = 5

    def __init__(self, build_cmd, run_cmd, valgrind_cmd,
                 valgrind_deduction, timeout=None, num_threads=None):
        super(LibcheckGrader, self).__init__(num_threads)

        self.build_cmd = shlex.split(build_cmd)
        self.run_cmd = shlex.split(run_cmd)
        self.valgrind_cmd = shlex.split(valgrind_cmd)
        self.valgrind_deduction = Fraction(valgrind_deduction)

        if timeout is None:
            self.timeout = self.DEFAULT_TIMEOUT
        else:
            self.timeout = timeout

    def list_prerequisites(self):
        return ['sudo apt-get install build-essential check valgrind']

    def grade_part(self, part, path, submission):
        return part.grade(path, self)

    def part_from_config_dict(self, config_dict):
        return LibcheckTest.from_config_dict(config_dict)

    def grade(self, submission, path, parts):
        try:
            process = run_process(self.build_cmd, cwd=path,
                                  timeout=self.timeout,
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
