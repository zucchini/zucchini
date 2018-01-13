import os
import decimal
from fractions import Fraction

from .submission import Submission


def grade_all(submission):
    return True


class Grade(object):
    """
    Hold information about a student's grade and format grade
    breakdowns. Abstracts away the more annoying assignment grading
    logic from the command-line interface.
    """

    # Round 0.5->1 when rounding fraction scores
    ROUNDING = decimal.ROUND_HALF_UP

    def __init__(self, assignment, submission):
        self._assignment = assignment
        self._submission = submission
        self._component_grades = self._submission.component_grades
        if self._component_grades is None:
            self._grade = None
        else:
            self._grade = self._assignment.calculate_grade(
                self._submission, self._component_grades)

    def __repr__(self):
        return '<Grade assignment={}, submission={}, component_grades={}, ' \
               'grade={}>'.format(self._assignment, self._submission,
                                  self._component_grades, self._grade)

    def gradable(self):
        """Return True if this submission is actually gradeable"""
        return self._submission.error is None

    def graded(self):
        """Return True if this submission has been graded, False otherwise."""
        return self._submission.graded

    def grade_ready(self):
        """Return True when this submission has a grade ready."""
        return not self.gradable() or self.graded()

    def grade(self):
        """Grade the submission and calculate the grade."""
        self._component_grades = self._assignment.grade_submission(
                self._submission)
        self._grade = self._assignment.calculate_grade(self._submission,
                                                       self._component_grades)

    def write_grade(self):
        """Write this grade to the submission metadata json."""
        # Need to put the components in the form used in the submission
        # meta.json
        grades = [grade.to_config_dict() for grade in self._component_grades]
        self._submission.write_grade(grades)

    def student_name(self):
        """Return the name of the student."""
        return self._submission.student_name

    def student_id(self):
        """Return the id of the student, or None if unset."""
        return self._submission.id

    @staticmethod
    def _decimal_out_of_100(frac):
        """
        Convert frac to a decimal.Decimal instance representing the
        score it represents out of 100.
        """
        # We want a number on [0,100], not [0,1]
        out_of_100 = frac * 100
        return decimal.Decimal(out_of_100.numerator) \
            / decimal.Decimal(out_of_100.denominator)

    @classmethod
    def _to_integer(cls, frac):
        """Round frac to an integer out of 100"""
        quotient = cls._decimal_out_of_100(frac)
        return int(quotient.to_integral_value(cls.ROUNDING))

    @classmethod
    def _two_decimals(cls, frac):
        """
        Convert frac to a string holding the number of points out of 100
        to two decimal points.
        """
        quotient = cls._decimal_out_of_100(frac)
        # Round to two decimal places
        return str(quotient.quantize(decimal.Decimal('1.00'), cls.ROUNDING))

    def score(self):
        """Return the grade as an integer out of 100."""
        if self._grade is None:
            return 0
        else:
            return self._to_integer(self._grade)

    def _breakdown_deductions(self):
        deducted_parts = []

        penalties = self._assignment.calculate_penalties(
            self._submission,
            self._assignment.calculate_raw_grade(self._component_grades))

        for penalty, penalty_delta in zip(self._assignment.penalties,
                                          penalties):
            if penalty_delta != 0:
                deducted_parts.append(
                    '{}: {}{}'.format(penalty.name,
                                      '+' if penalty_delta > 0 else '',
                                      self._two_decimals(penalty_delta)))

        for component, component_grade in zip(self._assignment.components,
                                              self._component_grades):
            if component_grade.is_broken():
                percentage_of_total = Fraction(component.weight,
                                               self._assignment.total_weight)
                component_points = self._two_decimals(percentage_of_total)
                deducted_parts.append('{}: -{} ({})'.format(
                    component.name, component_points, component_grade.error))
            else:
                for part, part_grade in zip(component.parts,
                                            component_grade.part_grades):
                    # To keep the breakdown easy to read, exclude parts
                    # which the student passed
                    if part_grade.score == 1:
                        continue

                    # Sometimes we want to warn students about things
                    # without penalizing them, so we'll set the weight of a
                    # part to 0. Handle that case:
                    if 0 in (component.weight, part.weight,
                             component.total_part_weight,
                             self._assignment.total_weight):
                        # The code below will add a + if it's needed
                        sign = '-' if part_grade.score < 1 else ''
                        delta = '{}0'.format(sign)
                    else:
                        # Calculate the percentage of the final grade
                        # lost/gained on this part. Basically, we want
                        # deviations from a perfect score.
                        percent_delta = component.weight * part.weight \
                            * (part_grade.score - 1) \
                            / component.total_part_weight \
                            / self._assignment.total_weight
                        delta = self._two_decimals(percent_delta)

                    if part_grade.deductions:
                        deductions = ' ({})'.format(
                            ', '.join(part_grade.deductions))
                    else:
                        deductions = ''

                    deducted_parts.append(
                        '{}: {}{}{}'.format(
                            part.part.description(),
                            '+' if part_grade.score > 1 else '',
                            delta, deductions))

        return deducted_parts

    def breakdown(self, grader_name):
        """
        Generate a grade breakdown for this grade. Each part whose score
        != 1 is included.
        """

        if self.gradable():
            breakdown = ', '.join(self._breakdown_deductions())
        else:
            breakdown = 'error: ' + self._submission.error

        return '{} -{}'.format(breakdown or 'Perfect!', grader_name)


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

    def is_interactive(self):
        """
        Return True if and only if grading will produce command-line
        prompts.
        """
        return self.assignment.is_interactive()

    def load_submissions(self):
        self.submissions = []

        # Walk through the immediate subdirectories of the submissions path.
        subdirectories = next(os.walk(self.submission_path))[1]

        for directory in subdirectories:
            full_path = os.path.join(self.submission_path, directory)

            submission = Submission.load_from_dir(self.assignment, full_path)

            if self.filter_fn(submission):
                self.submissions.append(submission)

    def submission_count(self):
        """Return the number of submissions to grade."""
        return len(self.submissions)

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
