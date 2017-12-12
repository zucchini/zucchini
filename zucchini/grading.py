"""Classes for storing scores for grading and generating logs and breakdowns"""

import decimal
import os
from datetime import datetime
from fractions import Fraction

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

        return ', '.join('{}: {}/{}{}'
                         .format(test.description(),
                                 self.round(test.score()),
                                 self.round(test.max_score()),
                                 '' if not test.deductions()
                                 else ' [{}]'.format(', '.join(test.deductions())))
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
        decimal.getcontext().rounding = decimal.ROUND_05UP
        quotient = decimal.Decimal(fraction.numerator) / decimal.Decimal(fraction.denominator)

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

    def deductions(self):
        """Return mapping of deduction names to deducted points for this test."""
        return self._deductions

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

        deductions = ','.join('{} deduction: -{}'
                              .format(deduction, StudentGrade.round(self._max_score * percent))
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
