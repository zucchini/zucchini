#!/usr/bin/env python3

"""Grade an LC-3 homework. Cobbled together in Fall 2k17 by Mr. Austin"""

import argparse
import decimal as d
import re
import subprocess
import sys
import os
import os.path
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

    def __init__(self, config_fp, submissions_dir, tests_dir, students=None):
        """Create a Grader by parsing config_fp and scanning submissions_dir"""

        # Round up for the sake of these keeeeds
        d.getcontext().rounding = d.ROUND_UP

        self.parse_config(config_fp, tests_dir)
        self.submissions_dir = submissions_dir
        self.tests_dir = tests_dir
        self.students = students if students is not None else \
                        self.find_students(submissions_dir)

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

    def parse_config(self, config_fp, tests_dir):
        """Parse config in the file-like object config_fp"""

        self.config = ConfigParser()
        self.config.read_file(config_fp)
        self.tests = [Test(description=self.config.get(section, 'description'),
                           xml_file=os.path.join(tests_dir, section),
                           asm_file=self.config.get(section, 'asmfile'),
                           weight=self.config.getint(section, 'weight'))
                      for section in self.config.sections() if section != 'META']
        total_weights = sum(int(t.weight) for t in self.tests)
        if total_weights == 0:
            raise ValueError('Test weights add up to 0 instead of 100. Did '
                             'you forget to add tests to the config file?')
        elif total_weights != 100:
            raise ValueError('Test weights do not add up to 100')
        self.description = self.config.get('META', 'description')
        self.runs = self.config.getint('META', 'runs', fallback=8)
        self.round_ = self.config.getint('META', 'round', fallback=2)
        self.human = self.config.get('META', 'human')

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
        tests = [(test.skip() if test in skip_tests else test.run(path, self.runs))
                 for test in self.tests]
        score = sum(test['score'] for test in tests)

        # Write gradeLog.txt
        with open(os.path.join(path, 'gradeLog.txt'), 'wb') as gradelog:
            now = datetime.now().isoformat()
            gradelog.write("{} grade report for `{}'\nDate: {}\nScore: {}\n========\n"
                           .format(self.description, student, now,
                                   self.round(score)).encode())
            for test in tests:
                gradelog.write('\n{}\nScore: {}/{}\n--------\n\n'
                               .format(test['description'], self.round(test['score']),
                                       self.round(test['max_score'])).encode())
                gradelog.write(test['output'])

        return {'score': score, 'tests': tests}

    def round(self, grade):
        """Round a grade to X decimal places"""
        return round(grade, self.round_)


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
    Associate a test xml file with the .asm file to test and a weight.
    """

    REGEX_RESULT_LINE = re.compile(r'^Run\s+(?P<run_number>\d+)\s+'
                                   r'Grade:\s+(?P<score>\d+)/(?P<max_score>\d+)\s+')

    def __init__(self, description, xml_file, asm_file, weight):
        self.description = description
        self.xml_file = xml_file
        self.asm_file = asm_file
        self.weight = weight

        if not os.path.isfile(xml_file):
            raise FileNotFoundError("could not find xml file `{}'".format(xml_file))

    def __str__(self):
        return "test `{}' on `{}'".format(self.xml_file, self.asm_file)

    def find_asm(self, directory):
        """
        Walk through the directory tree to find asm_file. Some students decide
        to put their submission in subdirectories for no reason.
        """

        for dirpath, _, files in os.walk(directory):
            if self.asm_file in files:
                return os.path.join(dirpath, self.asm_file)

        raise TestError(self, "Could not find asm `{}' in directory `{}'!"
                              .format(self.asm_file, directory))

    def run(self, directory, runs):
        """Run this test, returning the weighted grade"""

        asm_path = self.find_asm(directory)
        process = subprocess.run(['lc3test', self.xml_file, asm_path,
                                  '-runs={}'.format(runs)],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)

        if process.returncode != 0:
            raise TestError(self, 'lc3test returned {} != 0: {}'
                                  .format(process.returncode,
                                          process.stdout.decode().strip()))

        # Skip the last line because it's the "post your whole output on
        # piazza" line, and then grab the line for each run
        result_lines = process.stdout.splitlines()[-1 - runs:-1]

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

            if percent < percentages_min:
                percentages_min = percent

        weight = d.Decimal(self.weight)
        score = percentages_min * weight
        return {'score': score, 'max_score': weight,
                'description': self.description, 'output': process.stdout}

    def skip(self):
        """
        Return a result dict imitating the one returned by run(), except
        for skipping this test.
        """
        return {'score': d.Decimal(0), 'max_score': d.Decimal(self.weight),
                'description': self.description, 'output': b'(SKIPPED)\n'}

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
            score_breakdown = ', '.join('{}: {}/{}'
                                        .format(test['description'],
                                                grader.round(test['score']),
                                                grader.round(test['max_score']))
                                        for test in graded['tests'])
            print("Final grade for `{}': {}:\n{}. Total: {} -{}"
                  .format(student, grader.round(graded['score']),
                          score_breakdown, grader.round(graded['score']),
                          grader.get_human()))

            try:
                response = input('→ Try again? '
                                 '(Or print lc3test output (o)?) [y/N/o [testname]/q] ')
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
                    # Print full output
                    for test in graded['tests']:
                        print("Output for `{}':\n------------\n".format(test['description']))
                        sys.stdout.buffer.write(test['output'])
                else:
                    # Print output for specific test
                    test_arg = splat[1]
                    for test in graded['tests']:
                        if test['description'] == test_arg:
                            sys.stdout.buffer.write(test['output'])
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
                                     description='Grade LC-3 homework submissions (homework 6,7). '
                                                 'Run SubmissionFix.py first please.')
    parser.add_argument('-c', '--config', metavar='CONFIG_PATH', default='lc3grade.config',
                        type=argparse.FileType('r'), help='path to config file')
    parser.add_argument('-d', '--submissions-dir', metavar='DIR_PATH', default='.',
                        help='path to submissions directory')
    parser.add_argument('-t', '--tests-dir', metavar='TESTSDIR_PATH', default='.',
                        help='path to directory containing test xml files')
    parser.add_argument('-s', '--students', '--student', metavar='STUDENTS', default=None,
                        help='colon-delimited list of students to grade '
                             '(example: Adams, Austin:Murray, Kyle)')
    args = parser.parse_args(argv[1:])

    # Strip these characters from student names
    STRIP = ' \t\n/'
    # Choose : as the delimiter since it's not reserved in bash (unlike ;)
    students = None if args.students is None else \
               [student.strip(STRIP) for student in args.students.split(':') if student.strip(STRIP)]

    grader = Grader(config_fp=args.config, submissions_dir=args.submissions_dir,
                    tests_dir=args.tests_dir, students=students)


    for student in grader.get_students():
        # prompt() returns false when it gets `q', so exit in that case
        if not prompt(grader, student):
            return

if __name__ == '__main__':
    main(sys.argv)
