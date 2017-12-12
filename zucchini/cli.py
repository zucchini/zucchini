"""Command-line interface to Zucchini"""

import argparse
import subprocess
from .grader import Grader
from .grading import SetupError, TestError

# Use GNU readline for input()s if we can
try:
    import readline # pylint: disable=unused-import,wrong-import-order
except ImportError:
    pass

def main(argv, version=None):
    """Parse args, instantiate a Grader, and grade!"""

    parser = argparse.ArgumentParser(prog='zucc',
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter,
                                     description='Grade homework submissions according to '
                                                 'zucc.config. Run SubmissionFix.py first '
                                                 'please.')
    parser.add_argument('-V', '--version', action='version',
                        version='%(prog)s ' + (version or '(unknown version)'))
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

    interface = HeadlessInterface() if args.no_prompt else PromptInterface()
    Frontend(grader, interface).run()

class StopGrading(Exception):
    """Thrown when user aborts grading"""
    pass

class Frontend:
    """Invoke a Grader on all of its students, prompting user as necessary"""

    def __init__(self, grader, interface):
        self.grader = grader
        self.interface = interface

    def run(self):
        """
        Run the Grader for each of its students until user tells us to stop
        """

        for student in self.grader.get_students():
            try:
                self.grade_student(student)
            except StopGrading:
                return

    def failed_compile(self, student, setup_err):
        """
        Setup failed (usually because they did not submit anything or their code
        does not compile), so print a zero for the student given the provided
        Grader, student name, and SetupError instance.
        """

        self.interface.print_breakdown(self.grader.setup_abort(student, setup_err))


    def show_logs(self, grade, test=None):
        """
        Use a pager to display the logs for a given test, or the whole gradelog
        if test is None.
        """

        if test:
            gradelog = grade.test_gradelog(test)
            if gradelog is not None:
                self.interface.pager(gradelog)
            else:
                self.interface.warn("couldn't find that test. choices:\n{}".format(
                    '\n'.join(test.description for test in self.grader.tests)))
        else:
            self.interface.pager(grade.gradelog())

    def grade_student(self, student):
        """
        Attempt to grade this student's work until we succeed, prompting the
        user for guidance along the way.
        """

        done = False
        reprompt = False
        skip_tests = []
        setup_err = None
        test_err = None

        while not done:
            if not reprompt:
                try:
                    grade = self.grader.grade(student, skip_tests=skip_tests)
                except SetupError as err:
                    setup_err = err
                except TestError as err:
                    test_err = err
                else:
                    setup_err = test_err = None

            reprompt = False

            if setup_err:
                self.interface.warn("Setup error for `{}': {}".format(student, setup_err))
                if setup_err.output:
                    self.interface.warn(setup_err.output.decode())
                self.failed_compile(student, setup_err)

                resp = self.interface.ask_to_retry('n will give a 0 for this student')
                if resp is None:
                    reprompt = True
                elif not resp:
                    done = True
            elif test_err:
                self.interface.warn("Testing error for `{}': {}".format(student, test_err))

                resp = self.interface.ask_to_retry('n will give a 0 for this test')
                if resp is None:
                    reprompt = True
                elif not resp:
                    skip_tests.append(test_err.test)
            else:
                self.interface.print_breakdown(grade)

                resp = self.interface.ask_to_retry("(or print logs for a test "
                                                   "with `o <test name>'?)",
                                                   commands=('o',))
                if resp is None:
                    reprompt = True
                elif resp:
                    # So this is kinda a clean retry, try failed tests again
                    skip_tests = []
                    setup_err = test_err = None
                elif resp.was('o'):
                    reprompt = True
                    self.show_logs(grade, resp.arg())
                else:
                    done = True

class Interface:
    """Allow the user and Frontend to communicate."""

    def print_breakdown(self, grade):
        """
        Generate a student-friendly grading summary ("breakdown") from the Grader
        instance, student name, and grade results given and print it to stdout
        """
        pass

    def ask_to_retry(self, message, default='n', commands=()):
        """
        Prompt the user asking if they want to retry, returning a
        RetryPromptResponse matching their response. The RetryPromptResponse
        evaluates to True if they do want to retry.
        """
        pass

    def warn(self, message):
        """Print a warning"""
        pass

    def pager(self, data):
        """Display a bunch of data with a pager"""
        pass

class HeadlessInterface(Interface):
    """
    Discard warning messages and accept the default option for all prompts.
    """

    def print_breakdown(self, grade):
        print(grade.breakdown(grade))
        # Extra line is useful for visually separating students
        print()

    def ask_to_retry(self, message, default='n', commands=()):
        return RetryPromptResponse([default])

class PromptInterface(Interface):
    """Use the console to log warnings and prompt."""

    def print_breakdown(self, grade):
        print(grade.breakdown())

    def ask_to_retry(self, message, default='n', commands=()):
        understood = ('y', 'n', 'q') + commands
        cmd_help = '/'.join(cmd.upper() if cmd == default else cmd
                            for cmd in understood)

        try:
            text = input('→ Try again? {} [{}] '.format(message, cmd_help))
        except (KeyboardInterrupt, EOFError):
            # For courtesy, leave the shell prompt on a new line
            print()
            raise StopGrading()

        args = text.strip().lower().split(maxsplit=1)
        # Empty response, so assume no
        if not args:
            args = [default]
        elif args[0] == 'q':
            raise StopGrading()
        elif args[0] not in understood:
            print('come again? I only understand {}'.format(', '.join(understood)))
            return None

        return RetryPromptResponse(args)

    def warn(self, message):
        print(message)

    def pager(self, data):
        subprocess.run(['less'], input=data)

class RetryPromptResponse:
    """
    Represent a user's response to a retry prompt. Evaluates to True if they
    want to retry. You can poke at commands with was() to see if they want to
    ran a command instead.
    """

    def __init__(self, args):
        self.response = args[0]
        self._arg = args[1] if len(args) > 1 else None

    def __bool__(self):
        return self.response == 'y'

    def was(self, command):
        """Determine whether the response was command."""

        return self.response and self.response[0] == command

    def arg(self):
        """
        Return the argument passed to this command, or None if there was
        none.
        """

        return self._arg
