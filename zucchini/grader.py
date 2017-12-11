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

class Grader:
    """
    Execute lc3test for each configured test and calculate the final
    grade
    """

    def __init__(self, config_fp, submissions_dir, students=None,
                 exclude_students=None, skip_to=None):
        """Create a Grader by parsing config_fp and scanning submissions_dir"""

        # Round up for the sake of these keeeeds
        d.getcontext().rounding = d.ROUND_UP

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
        self.round_ = self.config.getint('META', 'round', fallback=2)
        self.human = self.config.get('META', 'human')
        self.tests = []
        for section in self.config.sections():
            if section in ('META', 'C', 'LC-3'):
                continue
            self.tests += self.backend.new_tests(name=section, **self.config[section])

        total_weights = sum(t.weight for t in self.tests)
        if total_weights == 0:
            raise ValueError('Test weights add up to 0 instead of 100. Did '
                             'you forget to add tests to the config file?')
        elif abs(d.Decimal(100) - total_weights) > d.Decimal('0.01'):
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

    def get_human(self):
        """Return grader's name"""
        return self.human

    def grade(self, student, skip_tests=None):
        """Grade student's work"""

        if skip_tests is None:
            skip_tests = []

        path = os.path.join(self.submissions_dir, student)

        # Default to the safe option, 1 thread, if we can't count the
        # number of CPUs
        num_threads = os.cpu_count() or 1
        threads = []
        test_queue = queue.Queue()
        result_queue = queue.Queue()

        try:
            self.backend.student_setup(path)
        except:
            self.backend.student_cleanup(path)
            raise

        tests = []
        for test in self.tests:
            if test in skip_tests:
                tests.append(test.skip())
            else:
                test_queue.put(test)

        for _ in range(num_threads):
            thread = threading.Thread(target=self.run_thread, args=(path, test_queue, result_queue))
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        while not result_queue.empty():
            result = result_queue.get(block=False)
            if isinstance(result, Exception):
                self.backend.student_cleanup(path)
                raise result
            else:
                tests.append(result)

        self.backend.student_cleanup(path)

        score = min(d.Decimal(100), sum(test['score'] for test in tests))

        # Write gradeLog.txt
        with open(os.path.join(path, 'gradeLog.txt'), 'wb') as gradelog:
            now = datetime.now().isoformat()
            gradelog.write("{} grade report for `{}'\nDate: {}\nScore: {}\n========\n"
                           .format(self.description, student, now,
                                   self.round(score)).encode())
            for test in tests:
                deductions = ','.join('{} deduction: -{}'.format(deduction, points)
                                      for deduction, points in test['deductions'].items())
                gradelog.write('\n{}\nScore: {}/{} ({})\n------------------\n\n'
                               .format(test['description'], self.round(test['score']),
                                       self.round(test['max_score']),
                                       deductions).encode())
                gradelog.write(test['output'])

        return {'score': score, 'tests': tests}

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

    def write_raw_gradelog(self, student, data):
        """
        Write the bytes given to the student's grader log. Useful for when
        compilation fails and you want to log the error, but you don't have any
        test results yet.
        """

        open(os.path.join(self.submissions_dir, student, 'gradeLog.txt'), 'wb').write(data)

    def round(self, grade):
        """Round a grade to X decimal places"""
        return round(grade, self.round_)

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

    def new_test(self, description, weight):
        """
        Create a list of Test objects for this Backend with the given config
        keys
        """
        pass

class LC3Backend(Backend):
    """Run tests with Brandon's lc3test"""

    def __init__(self, runs=8):
        self.runs = int(runs)

    def new_tests(self, **kwargs):
        """Return a list of new tests based on this ini section."""
        return [LC3Test(runs=self.runs, **kwargs)]

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
                raise SetupError(str(err))

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
            raise TestError(self, 'timeout of {} seconds expired for build command'
                                  .format(self.timeout))
        if process.returncode != 0:
            raise SetupError('build command {} exited with nonzero exit code: {}'
                             .format(self.build_cmd, process.returncode),
                             process.stdout)

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

        result = []
        tests = tests.split(',')
        for test in tests:
            test_name = self.testcase_fmt.format(test=test, category=name)
            test_weight = d.Decimal(weight) / d.Decimal(len(tests))
            result.append(CTest(timeout=self.timeout, get_tmpdir=lambda: self.tmpdir,
                                run_cmd=self.run_cmd, valgrind_cmd=self.valgrind_cmd,
                                weight=test_weight, name=test_name))

        return result

class SetupError(Exception):
    """An error occurring before actually running any tests"""

    def __init__(self, message, output=None):
        super().__init__(message)
        self.message = message
        if output is not None:
            self.output = output
        else:
            self.output = message.encode()

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
    calculate the score for this test
    """

    def __init__(self, name, description, weight):
        self.name = name
        self.description = description
        self.weight = weight

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
        Return a result dict imitating the one returned by run(), except
        for skipping this test.
        """
        return {'score': d.Decimal(0), 'max_score': d.Decimal(self.weight),
                'description': self.description, 'output': b'(SKIPPED)\n',
                'failed': True, 'deductions': {}}

class CTest(Test):
    """Run a libcheck test case both raw and through valgrind"""

    REGEX_SUMMARY = re.compile(r'\d+%:\s+Checks:\s+(?P<total>\d+),\s+'
                               r'Failures:\s+(?P<failures>\d+),\s+'
                               r'Errors:\s+(?P<errors>\d+)')

    def __init__(self, name, weight, get_tmpdir, run_cmd, valgrind_cmd,
                 timeout):
        self.description = self.testcase = name
        super().__init__(name, self.description, weight)
        self.get_tmpdir = get_tmpdir
        self.run_cmd = run_cmd
        self.valgrind_cmd = valgrind_cmd
        self.timeout = timeout
        # Hack: for now, use the weight as the leak deduction
        self.leak_deduction = weight


    def __str__(self):
        return "test case `{}'".format(self.testcase)

    def __repr__(self):
        return "test case `{}'".format(self.testcase)

    def run(self, directory):
        leak_deduction = d.Decimal(0)
        output = b''

        logfile_fp, logfile_path = tempfile.mkstemp(prefix='log-', dir=self.get_tmpdir())
        os.close(logfile_fp)
        logfile_basename = os.path.basename(logfile_path)

        # Timeout doesn't work when I say stdout=subprocess.PIPE,
        # stderr=subprocess.STDOUT.
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
                output += logfile_contents

                summary = logfile_contents.splitlines()[-1]
                match = self.REGEX_SUMMARY.match(summary.decode())
        except FileNotFoundError:
            raise TestError(self, 'could not locate test log file {}'.format(logfile_path))

        if not match:
            raise TestError(self, 'tester output is not in the expected libcheck format')

        total = d.Decimal(match.group('total'))
        failed = d.Decimal(match.group('errors')) + d.Decimal(match.group('failures'))
        score = d.Decimal(self.weight) * ((total - failed) / total)

        output += b'\nValgrind\n--------\n'

        if failed == total:
            valgrind_deduct = False
            output += b'failed this test, so skipping valgrind...\n'
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
                output += b'valgrind timed out, deducting full leak penalty...\n'
                valgrind_deduct = True
            else:
                output += valgrind_process.stdout
                valgrind_deduct = valgrind_process.returncode != 0

        if valgrind_deduct:
            leak_deduction = min(score, d.Decimal(self.leak_deduction))
            score -= leak_deduction
        else:
            leak_deduction = 0

        weight = d.Decimal(self.weight)
        return {'score': score, 'max_score': weight,
                'deductions': {'leak': leak_deduction},
                'failed': failed > 0 or valgrind_deduct,
                'description': self.description, 'output': output}

class LC3Test(Test):
    """
    Associate a test xml file with the .asm file to test and a weight.
    """

    REGEX_RESULT_LINE = re.compile(r'^Run\s+(?P<run_number>\d+)\s+'
                                   r'Grade:\s+(?P<score>\d+)/(?P<max_score>\d+)\s+.*?'
                                   r'Warnings:\s+(?P<warnings>\d+)$')

    def __init__(self, name, description, weight, asmfile, warning_deduction, runs):
        super().__init__(name, description, weight)
        self.xml_file = name
        self.asm_file = asmfile
        self.warning_deduction = int(warning_deduction)
        self.runs = runs

        if not os.path.isfile(self.xml_file):
            raise FileNotFoundError("could not find xml file `{}'".format(self.xml_file))

    def __str__(self):
        return "test `{}' on `{}'".format(self.xml_file, self.asm_file)


    def run(self, directory):
        """Run this test, returning the weighted grade"""

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

        # Skip the last line because it's the "post your whole output on
        # piazza" line, and then grab the line for each run
        result_lines = process.stdout.splitlines()[-1 - self.runs:-1]

        found_warnings = False
        percentages_min = d.Decimal('Infinity')

        for i, result_line in enumerate(result_lines):
            match = self.REGEX_RESULT_LINE.match(result_line.decode())
            if not match:
                raise TestError(self, 'lc3test produced some weird output. what the h*ck?')
            if int(match.group('run_number')) != i+1:
                raise TestError(self, 'lc3test run result lines are off!')
            score = int(match.group('score'))
            max_score = int(match.group('max_score'))
            percent = d.Decimal(score) / d.Decimal(max_score)
            found_warnings = found_warnings or int(match.group('warnings')) > 0

            if percent < percentages_min:
                percentages_min = percent

        weight = d.Decimal(self.weight)
        score = percentages_min * weight

        if found_warnings:
            # Don't deduct more points than they even have
            warning_deduction = min(score, d.Decimal(self.warning_deduction))
        else:
            warning_deduction = d.Decimal(0)
        score -= warning_deduction

        return {'score': score, 'max_score': weight,
                'deductions': {'warnings': warning_deduction},
                'description': self.description, 'output': process.stdout}
