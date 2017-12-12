"""Zucchini grading logic"""

import decimal as d
import re
import subprocess
import os
import os.path
import shutil
import tempfile
import threading
import queue
from configparser import ConfigParser
from datetime import datetime
from fractions import Fraction

class Grader:
    """
    Execute lc3test for each configured test and calculate the final
    grade
    """

    def __init__(self, config_fp, submissions_dir, students=None,
                 exclude_students=None, skip_to=None):
        """Create a Grader by parsing config_fp and scanning submissions_dir"""

        self.parse_config(config_fp)
        self.submissions_dir = submissions_dir
        self.students = students if students is not None else \
                        self.find_students(submissions_dir)
        if exclude_students is not None:
            self.students = [student for student in self.students
                             if student not in exclude_students]
        if skip_to is not None:
            self.students = self.students[self.students.index(skip_to):]

        if not self.students:
            raise FileNotFoundError('no student submissions found')
        elif not os.path.isdir(submissions_dir):
            raise FileNotFoundError("could not find submissions dir `{}'"
                                    .format(submissions_dir))
        else:
            # Check for non-existent students here so we blow up at startup
            # instead of right in the middle of grading, which would be
            # annoying
            for student in self.students:
                path = os.path.join(self.submissions_dir, student)
                if not os.path.isdir(path):
                    raise FileNotFoundError("could not find student submission "
                                            "dir `{}'".format(path))

    def parse_config(self, config_fp):
        """Parse config in the file-like object config_fp"""

        self.config = ConfigParser()
        self.config.read_file(config_fp)

        # Detect backend
        if ('LC-3' in self.config) == ('C' in self.config):
            raise ValueError('You need to configure either the LC-3 or C '
                             'backend, but not both')
        else:
            self.backend = CBackend(**self.config['C']) if 'C' in self.config else \
                           LC3Backend(**self.config['LC-3'])

        self.description = self.config.get('META', 'description')
        self.signoff = self.config.get('META', 'signoff')
        self.tests = []
        for section in self.config.sections():
            if section in ('META', 'C', 'LC-3'):
                continue
            self.tests.extend(self.backend.new_tests(name=section, **self.config[section]))

        total_weights = sum(t.weight for t in self.tests)

        if total_weights == 0:
            raise ValueError('Test weights add up to 0 instead of 100. Did '
                             'you forget to add tests to the config file?')
        elif total_weights != 100:
            raise ValueError('Test weights do not add up to 100')

    @staticmethod
    def find_students(submissions_dir):
        """
        Scan submissions_dir for student submission directories created by
        SubmissionFix.py
        """

        return sorted(ent for ent in os.listdir(submissions_dir) if ',' in ent)

    def get_students(self):
        """Return list of student names"""

        return self.students

    def grade(self, student, skip_tests=None):
        """
        Grade student's work, returning a StudentGrade instance containing
        results
        """

        if skip_tests is None:
            skip_tests = []

        path = os.path.join(self.submissions_dir, student)

        # Default to the safe assumption, 1 CPU, if we can't count the
        # number of CPUs
        num_threads = 2 * (os.cpu_count() or 1)
        threads = []
        test_queue = queue.Queue()
        result_queue = queue.Queue()
        grade = StudentGrade(self.description, student, self.signoff)

        try:
            self.backend.student_setup(path)

            for test in self.tests:
                if test in skip_tests:
                    grade.add_test_grade(test.skip())
                else:
                    test_queue.put(test)

            for _ in range(num_threads):
                thread = threading.Thread(target=self.run_thread,
                                          args=(path, test_queue, result_queue))
                thread.start()
                threads.append(thread)

            for thread in threads:
                thread.join()

            while not result_queue.empty():
                result = result_queue.get(block=False)
                if isinstance(result, Exception):
                    raise result
                else:
                    grade.add_test_grade(result)

            # Write gradeLog.txt
            self.write_raw_gradelog(student, grade.gradelog())
        finally:
            self.backend.student_cleanup(path)

        return grade

    @staticmethod
    def run_thread(path, test_queue, result_queue):
        """
        Dequeue Tests from test_queue until test_queue is empty, running them
        at the path given and enqueue the results in result_queue.
        """

        while True:
            try:
                test = test_queue.get(block=False)
            except queue.Empty:
                return

            try:
                result = test.run(path)
            except Exception as err: # pylint: disable=broad-except
                result_queue.put(err)
                return
            else:
                result_queue.put(result)

    def setup_abort(self, student, setup_err):
        """
        Handle a SetupError by writing error details to the grader log and
        returning a fake StudentGrade instance giving them a zero.
        """

        self.write_raw_gradelog(student, setup_err.output or setup_err.message.encode())
        return StudentGradeAborted(self.description, student, self.signoff, setup_err.summary)

    def write_raw_gradelog(self, student, data):
        """
        Write the bytes given to the student's grader log. Useful for when
        compilation fails and you want to log the error, but you don't have any
        test results yet.
        """

        open(os.path.join(self.submissions_dir, student, 'gradeLog.txt'), 'wb').write(data)

class StudentGrade:
    """
    Hold the results of running a student's code through a Grader
    instance.
    """

    def __init__(self, description, student, signoff):
        self.description = description
        self.student = student
        self.now = datetime.utcnow().isoformat()
        self.test_grades = []
        self.signoff = signoff

    def add_test_grade(self, test_grade):
        """
        Use this StudentTestGrade instance to calculate the grade for this
        student
        """

        self.test_grades.append(test_grade)

    def score(self):
        """Calculate this student's score as an int."""

        score = sum(test.score() for test in self.test_grades)
        # Integral score
        return self.round(score, places=0)

    def summary(self):
        """
        The student-friendly results summary printed between the grade and the
        signoff in the grade breakdown.
        """

        return ', '.join('{}: {}/{}'
                         .format(test.description(),
                                 self.round(test.score()),
                                 self.round(test.max_score()))
                         for test in self.test_grades if test.failed()) \
               or 'Perfect'

    def breakdown(self):
        """
        Construct a full student-friendly grade breakdown with a signoff and
        everything.
        """

        return "Final grade for `{}': {}:\n{}. Total: {}. {}" \
              .format(self.student, self.score(),
                      self.summary(),
                      self.score(), self.signoff)

    def test_gradelog(self, test_description):
        """
        Find and return the gradelog for a test grade with the given
        description, or return None if it doesn't exist.
        """

        for test_grade in self.test_grades:
            if test_grade.description() == test_description:
                return test_grade.gradelog()

        return None

    def gradelog(self):
        """Generate the gradeLog.txt for this grade."""

        result = "{} grade report for `{}'\nDate: {} UTC\nScore: {}\n" \
                 "\nBreakdown:\n{}\n========\n" \
                 .format(self.description, self.student, self.now,
                         self.score(), self.breakdown()).encode()

        for test_grade in self.test_grades:
            result += test_grade.gradelog()
            result += b'\n'

        return result

    @staticmethod
    def round(fraction, places=3):
        """Round this fraction for human display"""

        # Use decimal to round the fraction to an integer
        d.getcontext().rounding = d.ROUND_05UP
        quotient = d.Decimal(fraction.numerator) / d.Decimal(fraction.denominator)

        if places == 0:
            # round(D) for any Decimal instance D will return an int
            return round(quotient)
        else:
            # round(D, x) for any Decimal instance D will return a Decimal, so
            # convert to a string
            return str(round(quotient, places))

class StudentGradeAborted(StudentGrade):
    """Imitate a StudentGrade but for code that doesn't compile etc."""

    def __init__(self, description, student, signoff, summary):
        super().__init__(description, student, signoff)
        self._summary = summary

    def summary(self):
        return self._summary

class StudentTestGrade:
    """
    Hold the results of running a student's code through a given test.
    """

    def __init__(self, description, max_score):
        self._description = description
        self._percent_success = Fraction(0)
        self._max_score = Fraction(max_score)
        self._deductions = {}
        self._output = b''

    def description(self):
        """Return the description for this test."""
        return self._description

    def max_score(self):
        """Return the weight of this test."""
        return self._max_score

    def score(self):
        """Calculate the points this test resulted in."""
        return self._max_score * max(0, self._percent_success - sum(self._deductions.values()))

    def output(self):
        """Return the output of the test."""
        return self._output

    def failed(self):
        """
        Determine if this test failed so we can decide whether or not to
        include it in the breakdown.
        """
        return self._percent_success < 1 or bool(self._deductions)

    def add_output(self, output):
        """Append some bytes to the output of this test."""
        self._output += output

    def set_percent_success(self, percent_success):
        """
        Use the Fraction provided as the percentage of tests passed in the
        grade calculation.
        """
        self._percent_success = percent_success

    def deduct(self, deduct_name, deduct_percent=1):
        """
        Add a deduction with the given percentage of the test weight, or a 100%
        deduction if no percentage is provided.
        """
        self._deductions[deduct_name] = deduct_percent

    def gradelog(self):
        """Construct the gradeLog.txt section for this test."""

        deductions = ','.join('{} deduction: -{}'.format(deduction,
                              StudentGrade.round(self._max_score * percent))
                              for deduction, percent in self._deductions.items())
        deductions = deductions if not deductions else ' ({})'.format(deductions)
        result = '\n{}\nScore: {}/{}{}\n------------------\n\n' \
                 .format(self._description, StudentGrade.round(self.score()),
                         StudentGrade.round(self._max_score), deductions).encode()
        result += self._output
        return result

class StudentTestSkipped(StudentTestGrade):
    """
    Emulate StudentTestGrade, except with a 0 for a skipped test.
    """

    def __init__(self, description, max_score):
        super().__init__(description, max_score)
        self.add_output(b'(SKIPPED)')

class Backend:
    """
    Deal with an external grader, currently either lc3test or a C libcheck
    tester. Perform inital setup for a student to use this grader and then
    create Test instances ready-to-go
    """

    def student_setup(self, student_dir):
        """Do pre-grading setup for a given student"""
        pass

    def student_cleanup(self, student_dir):
        """Do post-grading cleanup for a given student"""
        pass

    def new_tests(self, description, weight):
        """
        Return an iterator of Test objects for this Backend created with the
        given config keys
        """
        pass

class LC3Backend(Backend):
    """Run tests with Brandon's lc3test"""

    def __init__(self, warning_deduction_percent, runs=100):
        self.runs = int(runs)
        self.warning_deduction_percent = Fraction(int(warning_deduction_percent), 100)

    def new_tests(self, **kwargs):
        """
        Return an LC3Test instance configured to test the given .asm file
        against the .xml file given for this ini section
        """

        yield LC3Test(runs=self.runs,
                      warning_deduction_percent=self.warning_deduction_percent,
                      **kwargs)

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

class SetupError(Exception):
    """An error occurring before actually running any tests"""

    def __init__(self, message, output, summary):
        super().__init__(message)
        self.message = message
        self.output = output
        self.summary = summary

class TestError(Exception):
    """A fatal error in running a test XML"""

    def __init__(self, test, message):
        super().__init__(message)
        self.test = test
        self.message = message

    def __str__(self):
        return '{}: {}'.format(self.test, self.message)

class Test:
    """
    Run a lc3test XML file or a libcheck test case and scrape its output to
    calculate the score for this test. Return a StudentTestGrade.
    """

    def __init__(self, name, description, weight):
        self.name = name
        self.description = description
        self.weight = Fraction(weight)

    @staticmethod
    def find_file(filename, directory):
        """
        Walk through the directory tree to find asm_file. Some students decide
        to put their submission in subdirectories for no reason.
        """

        for dirpath, _, files in os.walk(directory):
            if filename in files:
                return os.path.join(dirpath, filename)

        raise FileNotFoundError("Could not find deliverable `{}' in "
                                "directory `{}'!"
                                .format(filename, directory))

    def run(self, directory):
        """Run this test, returning the weighted grade"""
        pass

    def skip(self):
        """
        Return a fake StudentTestGrade which indicates we skipped this test.
        """
        return StudentTestSkipped(self.description, self.weight)

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
            raise TestError(self, 'tester returned {} != 0: {}'
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

class LC3Test(Test):
    """
    Associate a test xml file with the .asm file to test and a weight.
    """

    REGEX_RESULT_LINE = re.compile(r'^Run\s+(?P<run_number>\d+)\s+'
                                   r'Grade:\s+(?P<score>\d+)/(?P<max_score>\d+)\s+.*?'
                                   r'Warnings:\s+(?P<warnings>\d+)$')

    def __init__(self, name, description, weight, asmfile, warning_deduction_percent, runs):
        super().__init__(name, description, weight)
        self.xml_file = name
        self.asm_file = asmfile
        self.warning_deduction_percent = warning_deduction_percent
        self.runs = runs

        if not os.path.isfile(self.xml_file):
            raise FileNotFoundError("could not find xml file `{}'".format(self.xml_file))

    def __str__(self):
        return "test `{}' on `{}'".format(self.xml_file, self.asm_file)

    def run(self, directory):
        """Run this test, returning the weighted grade"""

        grade = StudentTestGrade(self.description, self.weight)

        try:
            asm_path = self.find_file(self.asm_file, directory)
        except FileNotFoundError as err:
            raise TestError(self, str(err))

        process = subprocess.run(['lc3test', self.xml_file, asm_path,
                                  '-runs={}'.format(self.runs)],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)

        if process.returncode != 0:
            raise TestError(self, 'lc3test returned {} != 0: {}'
                                  .format(process.returncode,
                                          process.stdout.decode().strip()))

        grade.add_output(process.stdout)

        # Skip the last line because it's the "post your whole output on
        # piazza" line, and then grab the line for each run
        result_lines = process.stdout.splitlines()[-1 - self.runs:-1]

        found_warnings = False
        percentages_min = None

        for i, result_line in enumerate(result_lines):
            match = self.REGEX_RESULT_LINE.match(result_line.decode())
            if not match:
                raise TestError(self, 'lc3test produced some weird output. what the h*ck?')
            if int(match.group('run_number')) != i+1:
                raise TestError(self, 'lc3test run result lines are off!')
            score = int(match.group('score'))
            max_score = int(match.group('max_score'))
            percent = Fraction(score, max_score)
            found_warnings = found_warnings or int(match.group('warnings')) > 0

            if percentages_min is None or percent < percentages_min:
                percentages_min = percent

        grade.set_percent_success(percentages_min)

        if found_warnings:
            grade.deduct('warnings', self.warning_deduction_percent)

        return grade
