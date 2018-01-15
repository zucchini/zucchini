import os
import decimal
from fractions import Fraction

from .submission import Submission

from .constants import SUBMISSION_GRADELOG_FILE


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
        self._grade = None

    def __repr__(self):
        return '<Grade assignment={}, submission={}, component_grades={}, ' \
               'grade={}>'.format(self._assignment, self._submission,
                                  self._component_grades, self._get_grade())

    def gradable(self):
        """Return True if this submission is actually gradeable"""
        return self._submission.error is None

    def graded(self):
        """Return True if this submission has been graded, False otherwise."""
        return self._submission.graded

    def grade_ready(self):
        """Return True when this submission has a grade ready."""
        return not self.gradable() or self.graded()

    def update(self, grade):
        """
        Copy the non-None component grades of grade into this Grade.
        """
        for i, component_grade in enumerate(grade._component_grades):
            if component_grade is not None:
                self._component_grades[i] = component_grade

    def grade(self, interactive=None):
        """
        Grade the submission and calculate the grade.
        If interactive is None (the default), grade all components; if
        True, grade only interactive components, and if False, grade
        only noninteractive components.
        """
        self._component_grades = self._assignment.grade_submission(
                self._submission, interactive=interactive)

    def _get_grade(self):
        """
        Calculate the grade for this submission, or return it if already
        calculated.
        """
        if self._grade is not None:
            return self._grade
        elif self._component_grades is None:
            return None
        else:
            self._grade = self._assignment.calculate_grade(
                self._submission, self._component_grades)
            return self._grade

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

    @classmethod
    def _left_pad(cls, num):
        return "%*.2f" % (5, num * 100)

    def score(self):
        """Return the grade as an integer out of 100."""
        grade = self._get_grade()
        if grade is None:
            return 0
        else:
            return self._to_integer(grade)

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

    def generate_gradelog(self):
        """
        Writes gradelog file to submission directory
        """

        gradelog_path = os.path.join(self._submission.path, SUBMISSION_GRADELOG_FILE)

        with open(gradelog_path, 'w') as f:

            m, s = divmod(self._submission.seconds_late, 60)
            h, m = divmod(m, 60)

            f.write("student_name: \"%s\", hours_late: %s\n\n" % (
                self._submission.student_name,
                "%d:%02d:%02d" % (h, m, s)))

            assignment_total_total_score = Fraction(0, 1)
            assignment_total_out_of_score = Fraction(0, 1)

            for component, component_grade in zip(self._assignment.components,
                                                  self._component_grades):
                if component_grade.is_broken():
                    percentage_of_total = Fraction(component.weight, self._assignment.total_weight)
                    component_points = self._left_pad(percentage_of_total)
                    earned_score = self._left_pad(Fraction(0, 1))
                    assignment_total_out_of_score += percentage_of_total
                    f.write("(%s / %s) [FAIL] TOTAL for %s: %s\n\n" % (
                        earned_score, component_points, component.name, component_grade.error))
                else:
                    component_total_total_score = Fraction(0, 1)
                    component_total_out_of_score = Fraction(0, 1)
                    for part, part_grade in zip(component.parts,
                                                component_grade.part_grades):
                        # calculate scores (deal with case where weight is 0)
                        if 0 not in (component.weight, part.weight,
                                 component.total_part_weight,
                                 self._assignment.total_weight):

                            # out of score for this part
                            out_of_score = Fraction(component.weight, self._assignment.total_weight) * \
                                           Fraction(part.weight, component.total_part_weight)
                            component_total_out_of_score += out_of_score

                            # total score for this part
                            total_score = out_of_score * part_grade.score
                            component_total_total_score += total_score
                        else:
                            total_score = Fraction(0,1)
                            out_of_score = Fraction(0,1)

                        # gets short name for class
                        dot_idx = part.part.cls.rfind(".")
                        short_class_name = part.part.cls if dot_idx == -1 else part.part.cls[dot_idx+1:]

                        # print part score
                        if part_grade.score == 1:
                            f.write("(%s / %s) [PASS] %s: %s.%s\n" % (
                                self._left_pad(total_score), self._left_pad(out_of_score),
                                component.name, short_class_name, part.part.name))
                        else:
                            f.write("(%s / %s) [FAIL] %s: %s.%s - %s\n" % (
                                self._left_pad(total_score), self._left_pad(out_of_score),
                                component.name, short_class_name, part.part.name, part_grade.log))

                    # print totals for assignment component
                    f.write("(%s / %s) [%s] TOTAL for %s\n\n" % (
                        self._left_pad(component_total_total_score),
                        self._left_pad(component_total_out_of_score),
                        "PASS" if component_total_total_score == component_total_out_of_score else "FAIL",
                        component.name))

                    assignment_total_out_of_score += component_total_out_of_score
                    assignment_total_total_score += component_total_total_score

            # print totals for complete assignment
            f.write("(%s / %s) [%s] TOTAL for %s (without penalties)\n" % (
                self._left_pad(assignment_total_total_score),
                self._left_pad(assignment_total_out_of_score),
                "PASS" if assignment_total_out_of_score == assignment_total_total_score else "FAIL",
                self._assignment.name))

            # print penalties (like being late)
            penalties = self._assignment.calculate_penalties(
                self._submission,
                self._assignment.calculate_raw_grade(self._component_grades))

            # print out penalties
            for penalty, penalty_delta in zip(self._assignment.penalties,
                                              penalties):
                if penalty_delta != 0:
                    f.write("(%s) Penalty: %s\n" % (
                        self._left_pad(penalty_delta),
                        penalty.name
                    ))

            f.write("\n-----------------------\n| %6.2f%% FINAL SCORE |\n-----------------------" % (self._grade * 100))


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

    def has_interactive(self):
        """
        Return True if and only if grading will produce command-line
        prompts.
        """
        return self.assignment.has_interactive()

    def has_noninteractive(self):
        """
        Return True if and only if grading will produce command-line
        prompts.
        """
        return self.assignment.has_noninteractive()

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

    def grade(self, interactive=None):
        """
        Grade all submissions, returning an iterable of Grade instances.
        If interactive is None (the default), grade all components; if
        True, grade only interactive components, and if False, grade
        only noninteractive components.
        """

        for submission in self.submissions:
            grade = Grade(self.assignment, submission)
            grade.grade(interactive)
            grade.write_grade()
            grade.generate_gradelog()

            yield grade

    def grades(self):
        """Return a list of all grades"""

        for submission in self.submissions:
            yield Grade(self.assignment, submission)
