"""Zucchini C (libcheck) backend"""

import os
import re
import shutil
import subprocess
import tempfile
from fractions import Fraction
from ..grading import Backend, Test, StudentTestGrade, TestError, SetupError

class CBackend(Backend):
    """Run tests through a libcheck C tester"""

    def __init__(self, timeout, cfiles, tests_dir, build_cmd, run_cmd,
                 valgrind_cmd, testcase_fmt):
        self.timeout = float(timeout)
        self.cfiles = cfiles.split()
        self.tests_dir = tests_dir
        self.build_cmd = build_cmd
        self.run_cmd = run_cmd
        self.valgrind_cmd = valgrind_cmd
        self.tmpdir = None
        self.testcase_fmt = testcase_fmt

    def student_setup(self, student_dir):
        """
        Create a temporary directory inside the student directory and
        compile a student's code by running build_cmd from
        zucc.config
        """

        self.tmpdir = tempfile.mkdtemp(prefix='zucc-', dir=student_dir)

        for cfile in self.cfiles:
            try:
                cfile_path = CTest.find_file(cfile, student_dir)
            except FileNotFoundError as err:
                raise SetupError(str(err), None, 'no submission')

            shutil.copy(cfile_path, os.path.join(self.tmpdir, cfile))

        for graderfile in os.listdir(self.tests_dir):
            dest_file = os.path.join(self.tmpdir, graderfile)
            # Don't clobber student's files
            if not os.path.exists(dest_file):
                shutil.copy2(os.path.join(self.tests_dir, graderfile), dest_file)

        try:
            process = subprocess.run(self.build_cmd.split(), cwd=self.tmpdir,
                                     timeout=self.timeout, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)
        except subprocess.TimeoutExpired:
            raise SetupError('timeout of {} seconds expired for build command'
                             .format(self.timeout), process.stdout,
                             'compilation timed out')
        if process.returncode != 0:
            raise SetupError('build command {} exited with nonzero exit code: {}'
                             .format(self.build_cmd, process.returncode),
                             process.stdout, 'did not compile')

    def student_cleanup(self, student_dir):
        """
        Delete temporary build/test directory created by student_setup()
        """

        shutil.rmtree(self.tmpdir)

    def new_tests(self, tests, name, weight):
        """
        Create a C tester instance which knows about the temporary directory
        created by student_setup()
        """

        tests = tests.split(',')
        for test in tests:
            test_name = self.testcase_fmt.format(test=test, category=name)
            test_weight = Fraction(int(weight), len(tests))
            yield CTest(timeout=self.timeout, get_tmpdir=lambda: self.tmpdir,
                        run_cmd=self.run_cmd, valgrind_cmd=self.valgrind_cmd,
                        weight=test_weight, name=test_name)

class CTest(Test):
    """Run a libcheck test case both raw and through valgrind"""

    REGEX_SUMMARY = re.compile(r'\d+%:\s+Checks:\s+(?P<total>\d+),\s+'
                               r'Failures:\s+(?P<failures>\d+),\s+'
                               r'Errors:\s+(?P<errors>\d+)')

    def __init__(self, name, weight, get_tmpdir, run_cmd, valgrind_cmd,
                 timeout):
        super().__init__(name, name, weight)
        self.testcase = name
        self.get_tmpdir = get_tmpdir
        self.run_cmd = run_cmd
        self.valgrind_cmd = valgrind_cmd
        self.timeout = timeout

    def __str__(self):
        return "test case `{}'".format(self.testcase)

    def __repr__(self):
        return "test case `{}'".format(self.testcase)

    def run(self, directory):
        grade = StudentTestGrade(self.description, self.weight)

        logfile_fp, logfile_path = tempfile.mkstemp(prefix='log-', dir=self.get_tmpdir())
        # Don't leak fds
        os.close(logfile_fp)
        logfile_basename = os.path.basename(logfile_path)

        process = subprocess.run(self.run_cmd.format(test=self.testcase,
                                                     logfile=logfile_basename).split(),
                                 env={'CK_DEFAULT_TIMEOUT': str(self.timeout)},
                                 cwd=self.get_tmpdir(), stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)

        if process.returncode != 0:
            raise TestError(self,
                            'tester returned {} != 0: {}'
                            .format(process.returncode,
                                    (process.stdout or b'').decode().strip()))

        # Read the test summary from the log file so that student printf()s
        # don't mess up our parsing.
        try:
            with open(logfile_path, 'rb') as logfile:
                logfile_contents = logfile.read()
                grade.add_output(logfile_contents)

                summary = logfile_contents.splitlines()[-1]
                match = self.REGEX_SUMMARY.match(summary.decode())
        except FileNotFoundError:
            raise TestError(self, 'could not locate test log file {}'.format(logfile_path))

        if not match:
            raise TestError(self, 'tester output is not in the expected libcheck format')

        total = int(match.group('total'))
        failed = int(match.group('errors')) + int(match.group('failures'))
        grade.set_percent_success(Fraction(total - failed, total))

        grade.add_output(b'\nValgrind\n--------\n')

        if grade.failed():
            valgrind_deduct = False
            grade.add_output(b'failed this test, so skipping valgrind...\n')
        else:
            # When running valgrind, we need to set CK_FORK=no, else we're gonna
            # get a ton of bogus reported memory leaks. However, CK_FORK=no will
            # break libcheck timeouts, so make sure to handle timeouts here with
            # subprocess
            try:
                valgrind_cmd = self.valgrind_cmd.format(test=self.testcase,
                                                        logfile=logfile_basename).split()
                valgrind_process = subprocess.run(valgrind_cmd,
                                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                  env={'CK_FORK': 'no'}, cwd=self.get_tmpdir(),
                                                  timeout=self.timeout)
            except subprocess.TimeoutExpired:
                grade.add_output(b'valgrind timed out, deducting full leak penalty...\n')
                valgrind_deduct = True
            else:
                grade.add_output(valgrind_process.stdout or b'(success)')
                valgrind_deduct = valgrind_process.returncode != 0

        # Give no credit for tests failing valgrind
        if valgrind_deduct:
            grade.deduct('valgrind')

        return grade
