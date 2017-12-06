#!/usr/bin/env python3

"""Grade an LC-3 homework. Cobbled together in Fall 2k17 by Mr. Austin"""

import argparse
import decimal as d
import re
import subprocess
import sys
import os
import os.path
import shutil
import tempfile
import threading
import queue
from configparser import ConfigParser
from datetime import datetime

# Use GNU readline for input()s if we can
try:
    import readline
except ImportError:
    pass

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

        # 8 threads
        THREADS = 8
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

        for i in range(THREADS):
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
        while True:
            try:
                test = test_queue.get(block=False)
            except queue.Empty:
                return

            try:
                result = test.run(path)
            except Exception as err:
                result_queue.put(err)
                return
            else:
                result_queue.put(result)

    def write_raw_gradelog(self, student, data):
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
        lc3grade.config
        """

        self.tmpdir = tempfile.mkdtemp(prefix='lc3grade-', dir=student_dir)

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
                'deductions': {}}

class CTest(Test):
    """Run a libcheck test case both raw and through valgrind"""

    REGEX_SUMMARY = re.compile(r'\d+%:\s+Checks:\s+(?P<total>\d+),\s+'
                               r'Failures:\s+(?P<failures>\d+),\s+'
                               r'Errors:\s+(?P<errors>\d+)')

    def __init__(self, name, weight, get_tmpdir, run_cmd,
                 valgrind_cmd, timeout, leak_deduction=0):
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
        process = subprocess.run(self.run_cmd.format(test=self.testcase, logfile=logfile_basename).split(),
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
                valgrind_process = subprocess.run(self.valgrind_cmd.format(test=self.testcase, logfile=logfile_basename).split(),
                                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                                  env={'CK_FORK': 'no'}, cwd=self.get_tmpdir(),
                                                  timeout=self.timeout)
            except subprocess.TimeoutExpired:
                output += b'valgrind timed out, deducting full leak penalty...\n'
                valgrind_deduct=True
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

def pager(stdin):
    """Open less to view the output of a test"""

    subprocess.run(['less'], input=stdin)

def print_breakdown(grader, student, graded):
    score_breakdown = ', '.join('{}: {}/{}'
                                .format(test['description'],
                                        grader.round(test['score']),
                                        grader.round(test['max_score']))
                                for test in graded['tests'] if test['score'] < test['max_score'])
    print("Final grade for `{}': {}:\n{}. Total: {} -{}"
          .format(student, grader.round(graded['score']),
                  score_breakdown or 'Perfect', grader.round(graded['score']),
                  grader.get_human()))

def failed_compile(grader, student, err):
    print("Final grade for `{}': 0:\n0 (did not compile) -{}".format(student, grader.get_human()))
    grader.write_raw_gradelog(student, err.output)

def headless_grade(grader, student):
    skip_tests = []

    while True:
        try:
            graded = grader.grade(student, skip_tests=skip_tests)
        except SetupError as err:
            failed_compile(grader, student, err)
            # Blank line makes it a lot easier to visually separate students
            print()
            return
        except TestError as err:
            skip_tests.append(err.test)
        else:
            break

    print_breakdown(grader, student, graded)
    # Blank line makes it a lot easier to visually separate students
    print()

# XXX This function is really ugly (sorry), fix it
def prompt(grader, student):
    """
    Print grades for student and show a prompt. Return False to exit
    now, and True to continue to the next student.
    """

    state = 'retry'
    skip_tests = []

    while state in ('retry', 'reprompt'):
        try:
            if state == 'retry':
                graded = grader.grade(student, skip_tests=skip_tests)
        except SetupError as err:
            print("Setup error for `{}': {}".format(student, err))
            print(err.output.decode())
            failed_compile(grader, student, err)
            try:
                response = input('→ Try again? N will give a 0 for this student [y/N/q] ').lower()
            except (KeyboardInterrupt, EOFError):
                # For courtesy, leave the shell prompt on a new line
                print()
                # Exit now
                return False

            if response == 'q':
                # Exit now
                return False
            elif response != 'y':
                return True
            state = 'retry'
        except TestError as err:
            print("Testing error for `{}': {}".format(student, err))
            try:
                response = input('→ Try again? N will give a 0 for this test [y/N/q] ').lower()
            except (KeyboardInterrupt, EOFError):
                # For courtesy, leave the shell prompt on a new line
                print()
                # Exit now
                return False

            if response == 'q':
                # Exit now
                return False
            elif response != 'y':
                # Try again and skip this test (y will try again without
                # skipping the test)
                skip_tests.append(err.test)
            state = 'retry'
        else:
            print_breakdown(grader, student, graded)

            try:
                response = input('→ Try again? '
                                 '(Or print tester output (o)?) [y/N/o [testname]/q] ')
            except (KeyboardInterrupt, EOFError):
                # For courtesy, leave the shell prompt on a new line
                print()
                # Exit now
                return False

            if response.lower() == 'q':
                # Exit now
                return False
            elif response.lower() == 'y':
                state = 'retry'
                # So this is kinda a clean retry, try failed tests again
                skip_tests = []
            elif response.lower().startswith('o'):
                state = 'reprompt'

                splat = response.split(maxsplit=1)
                if len(splat) == 1:
                    buf = b''
                    # Print full output
                    for test in graded['tests']:
                        buf += "Output for `{}':\n".format(test['description']).encode()
                        for deduction, points in test['deductions'].items():
                            buf += "{} deduction: -{}\n" \
                                   .format(deduction, points) \
                                   .encode()
                        buf += "------------\n".encode()
                        buf += test['output']
                        # Separate output of different tests with some blank lines
                        buf += b'\n\n'
                    pager(buf)
                else:
                    # Print output for specific test
                    test_arg = splat[1]
                    for test in graded['tests']:
                        if test['description'] == test_arg:
                            pager(''.join('{} deduction: -{}\n'
                                          .format(deduction, points)
                                          for deduction, points
                                          in test['deductions'].items()).encode() +
                                  test['output'])
                            break
                    else:
                        print("couldn't find that test. choices:\n{}"
                              .format('\n'.join(test['description']
                                                for test in graded['tests'])))
            else:
                state = 'next'

    # Continue to the next student instead of exiting now
    return True

def main(argv):
    """Parse args, instantiate a Grader, and grade!"""

    parser = argparse.ArgumentParser(prog='python3 grader.py',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     description='Grade homework submissions according to '
                                                 'lc3grade.config. Run SubmissionFix.py '
                                                 'first please.')
    parser.add_argument('-c', '--config', metavar='CONFIG_PATH', default='lc3grade.config',
                        type=argparse.FileType('r'), help='path to config file')
    parser.add_argument('-d', '--submissions-dir', metavar='DIR_PATH', default='.',
                        help='path to submissions directory')
    parser.add_argument('-s', '--students', '--student', metavar='STUDENTS', default=None,
                        help='colon-delimited list of students to grade '
                             '(example: Adams, Austin:Murray, Kyle)')
    parser.add_argument('-e', '--exclude-students', '--exclude-student', metavar='STUDENTS',
                        default=None,
                        help='colon-delimited list of students to exclude from grading '
                             '(example: Adams, Austin:Murray, Kyle)')
    parser.add_argument('-S', '--skip-to', '--skip', metavar='STUDENT', default=None,
                        help='skip straight to this student for grading, '
                             'ignoring previous students in the list. '
                             'useful if you accidentally hit control-C while grading')
    parser.add_argument('-n', '--no-prompt', action='store_true',
                        help='run all students without showing the prompt')
    args = parser.parse_args(argv[1:])

    # Strip these characters from student names
    strip = lambda student: None if student is None else student.strip(' \t\n/')
    # Choose : as the delimiter since it's not reserved in bash (unlike ;)
    splitstrip = lambda students: None if students is None else \
                                  [strip(student) for student in students.split(':') \
                                  if strip(student)]

    grader = Grader(config_fp=args.config, submissions_dir=args.submissions_dir,
                    students=splitstrip(args.students),
                    exclude_students=splitstrip(args.exclude_students),
                    skip_to=strip(args.skip_to))


    for student in grader.get_students():
        if args.no_prompt:
            headless_grade(grader, student)
        else:
            # prompt() returns false when it gets `q', so exit in that case
            if not prompt(grader, student):
                return

if __name__ == '__main__':
    main(sys.argv)
