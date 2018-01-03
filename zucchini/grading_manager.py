import os
import decimal

from .submission import Submission


def grade_all(submission_name):
    return True


class Grade(object):
    """
    Hold information about a student's grade and format grade
    breakdowns. Abstracts away the more annoying assignment grading
    logic from the command-line interface.
    """

    def __init__(self, assignment, submission):
        self._assignment = assignment
        self._submission = submission
        self._component_grades = self._submission.component_grades
        if self._component_grades is None:
            self._grade = None
        else:
            self._grade = self._assignment.calculate_grade(
                self._component_grades)

    def graded(self):
        """Return True if this submission has been graded, False otherwise."""
        return self._submission.graded

    def grade(self):
        """Grade the submission and calculate the grade."""
        self._component_grades = self._assignment.grade_submission(
                self._submission)
        self._grade = self._assignment.calculate_grade(self._component_grades)

    def write_grade(self):
        """Write this grade to the submission metadata json."""
        # Need to put the components in the form used in the submission
        # meta.json
        grades = [grade.to_config_dict() for grade in self._component_grades]
        self._submission.write_grade(grades)

    def student_name(self):
        """Return the name of the student."""
        return self._submission.student_name

    def score(self):
        """Return the grade as an integer out of 100."""
        # We want a number on [0,100], not [0,1]
        out_of_100 = self._grade * 100
        # Now, use decimal to round the fraction to an integer
        # Round 0.5 -> 1
        quotient = decimal.Decimal(out_of_100.numerator) \
            / decimal.Decimal(out_of_100.denominator)
        # round(D) for any Decimal object D will return an int
        return int(quotient.to_integral_value(decimal.ROUND_05UP))


class GradingManager(object):
    def __init__(self, assignment, submission_path, filter_fn=grade_all):
        # Here we've abstracted away the submission filter. If the user wants
        # to selectively grade some submissions, the CLI will provide a filter
        # function that, when given a submission's name, returns a boolean
        # denoting whether or not the submission should be graded.
        # The grade_all function above is an example.

        self.assignment = assignment
        # TODO: Check if it exists ^

        self.submission_path = submission_path
        # TODO: Check if it exists ^

        self.filter_fn = filter_fn
        # TODO: Check if it exists ^

        self.submissions = []

        self.load_submissions()

    def load_submissions(self):
        self.submissions = []

        # Walk through the immediate subdirectories of the submissions path.
        subdirectories = next(os.walk(self.submission_path))[1]

        for directory in subdirectories:
            if not self.filter_fn(directory):
                continue

            full_path = os.path.join(self.submission_path, directory)

            submission = Submission.load_from_dir(self.assignment, full_path)
            self.submissions.append(submission)
            # TODO: Handle broken submissions right here

    def grade(self):
        """Grade all submissions, returning an iterable of Grade instances."""

        for submission in self.submissions:
            grade = Grade(self.assignment, submission)
            grade.grade()
            grade.write_grade()

            yield grade

    def grades(self):
        """Return a list of all grades"""

        for submission in self.submissions:
            yield Grade(self.assignment, submission)
