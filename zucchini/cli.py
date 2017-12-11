"""Command-line interface to Zucchini"""

import argparse
import subprocess
from .grader import Grader, SetupError, TestError

# Use GNU readline for input()s if we can
try:
    import readline # pylint: disable=unused-import,wrong-import-order
except ImportError:
    pass

def main(argv):
    """Parse args, instantiate a Grader, and grade!"""

    parser = argparse.ArgumentParser(prog='python3 grader.py',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     description='Grade homework submissions according to '
                                                 'zucc.config. Run SubmissionFix.py first '
                                                 'please.')
    parser.add_argument('-c', '--config', metavar='CONFIG_PATH', default='zucc.config',
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

def pager(stdin):
    """Open less to view the output of a test"""

    subprocess.run(['less'], input=stdin)

def print_breakdown(grader, student, graded):
    """
    Generate a student-friendly grading summary ("breakdown") from the Grader
    instance, student name, and grade results given and print it to stdout
    """

    score_breakdown = ', '.join('{}: {}/{}'
                                .format(test['description'],
                                        grader.round(test['score']),
                                        grader.round(test['max_score']))
                                for test in graded['tests'] if test['failed'])
    print("Final grade for `{}': {}:\n{}. Total: {} -{}"
          .format(student, grader.round(graded['score']),
                  score_breakdown or 'Perfect', grader.round(graded['score']),
                  grader.get_human()))

def failed_compile(grader, student, err):
    """
    Setup failed (usually because they did not submit anything or their code
    does not compile), so print a zero for the student given the provided
    Grader, student name, and SetupError instance.
    """

    print("Final grade for `{}': 0:\n0 (did not compile) -{}".format(student, grader.get_human()))
    grader.write_raw_gradelog(student, err.output)

def headless_grade(grader, student):
    """
    Grade this student using the Grader provided non-interactively. So no
    prompts, just results to stdout. Useful if you're grading 400+ submissions
    and don't want to develop carpal tunnel from pressing enter constantly.
    """

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
