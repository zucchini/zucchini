import os
import decimal
import hashlib
import json
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

    # constants for gradelog files
    ZUCCHINI_BEGIN_GRADELOG = 'ZUCCHINI_BEGIN_GRADELOG'
    ZUCCHINI_END_GRADELOG = 'ZUCCHINI_END_GRADELOG'
    READ_BUFFER_SIZE = 65536

    def __init__(self, assignment, submission, max_score=100):
        self._assignment = assignment
        self._submission = submission
        self._max_score = max_score
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

    def get_gradelog_path(self):
        # Put in the same directory as the metadata file
        submission_dir = os.path.dirname(self._submission.metadata_path)
        return os.path.join(submission_dir, SUBMISSION_GRADELOG_FILE)

    def get_gradelog_hash(self):
        with open(self.get_gradelog_path(), 'r') as f:
            gradelog_data = f.read()
            idx = gradelog_data.index(
                self.ZUCCHINI_END_GRADELOG) + len(self.ZUCCHINI_END_GRADELOG)
            return gradelog_data[idx:].strip()

    def serialized_component_grades(self):
        """
        Return component grades serialized with to_config_dict(). Useful
        for logging.
        """
        return [component_grade.to_config_dict()
                for component_grade in self._component_grades]

    def dump_component_grades(self, fp):
        """Dump component grades as JSON to file-like object fp"""
        json.dump(self.serialized_component_grades(), fp)

    def write_grade(self):
        """Write this grade to the submission metadata json."""
        # Need to put the components in the form used in the submission
        # meta.json
        self._submission.write_grade(self.serialized_component_grades())

    def student_name(self):
        """Return the name of the student."""
        return self._submission.student_name

    def student_id(self):
        """Return the id of the student, or None if unset."""
        return self._submission.id

    def to_float(self, frac):
        """
        Convert a fraction on [0,1] to a float to two decimal points.
        Should be used for ballparking, NOT calculations.
        """
        # We want a number on [0,100], not [0,1]
        out_of_max = frac * self._max_score
        return float(out_of_max.numerator) / float(out_of_max.denominator)

    def _decimal_out_of_max(self, frac):
        """
        Convert frac to a decimal.Decimal instance representing the
        score it represents out of 100 (or whatever the max score is).
        """
        # We want a number on [0,100], not [0,1]
        out_of_max = frac * self._max_score
        return decimal.Decimal(out_of_max.numerator) \
            / decimal.Decimal(out_of_max.denominator)

    def to_integer(self, frac):
        """
        Round frac to an integer out of 100 (or whatever the max score
        is)
        """
        quotient = self._decimal_out_of_max(frac)
        return int(quotient.to_integral_value(self.ROUNDING))

    def two_decimals(self, frac):
        """
        Convert frac to a string holding the number of points out of 100
        (or whatever the max score is) to two decimal points.
        """
        quotient = self._decimal_out_of_max(frac)
        # Round to two decimal places
        return str(quotient.quantize(decimal.Decimal('1.00'), self.ROUNDING))

    def _left_pad(self, num):
        return "%*.2f" % (5, num * self._max_score)

    def computed_grade(self):
        """
        Return a ComputedGrade instance holding the tree of computed
        grading data for this grade.
        """
        return self._get_grade()

    def score(self):
        """
        Return the grade as an integer out of 100 (or whatever the
        max score is).
        """
        grade = self._get_grade()
        if grade is None:
            return 0
        else:
            return self.to_integer(grade.grade)

    def _breakdown_deductions(self, grade):
        deducted_parts = []

        for penalty in grade.penalties:
            if penalty.points_delta != 0:
                sign = '+' if penalty.points_delta > 0 else ''
                points = self.two_decimals(penalty.points_delta)
                deducted_parts.append('{}: {}{}'.format(penalty.name, sign,
                                                        points))

        for component in grade.components:
            if component.error is not None:
                # Component-level error
                points = self.two_decimals(component.points_delta)
                deducted_parts.append('{}: {} ({})'.format(
                    component.name, points, component.error))
            else:
                for part in component.parts:
                    # To keep the breakdown easy to read, exclude parts
                    # which the student passed
                    if part.grade == 1:
                        continue

                    delta = self.two_decimals(part.points_delta)

                    if part.deductions:
                        deductions = ' ({})'.format(
                            ', '.join(part.deductions))
                    else:
                        deductions = ''

                    plus_sign = '+' if part.grade > 1 else ''
                    deducted_parts.append(
                        '{}: {}{}{}'.format(part.name, plus_sign,
                                            delta, deductions))

        return deducted_parts

    def breakdown(self, grader_name):
        """
        Generate a grade breakdown for this grade. Each part whose score
        != 1 is included.
        """

        if self.gradable():
            deductions = self._breakdown_deductions(self._get_grade())
            breakdown = ', '.join(deductions)
        else:
            breakdown = 'error: ' + self._submission.error

        return '{} -{}'.format(breakdown or 'Perfect!', grader_name)

    def _files_tuple_mapper(self, common_path, x):
        file_path = x[0]
        file_path_str = x[1]

        start_idx = file_path_str.find(common_path) + len(common_path)
        file_path_str_abbrv = file_path_str[start_idx:]

        file_hash = x[3]
        return (file_path, file_path_str, file_path_str_abbrv, file_hash)

    def generate_gradelog(self):
        """
        Writes gradelog file to submission directory
        """

        grade = self._get_grade()
        gradelog_path = self.get_gradelog_path()

        with open(gradelog_path, 'w') as f:
            # this used to be student's name, but that might be FERPA
            gradelog_path_byte_encoded \
                = str(self.get_gradelog_path()).encode('utf-8')
            f.write("%s\n\n%s\nstudent_name: \"%s\"" % (
                self.ZUCCHINI_BEGIN_GRADELOG,
                self._assignment.name,
                hashlib.sha224(gradelog_path_byte_encoded).hexdigest()[0:31]))

            if self._submission.seconds_late is not None:
                m, s = divmod(self._submission.seconds_late, 60)
                h, m = divmod(m, 60)

                f.write(", hours_late: %s" % "%d:%02d:%02d" % (h, m, s))

            f.write("\n\n")

            assignment_pass = True

            for component in grade.components:
                if component.error is not None:
                    assignment_pass = False
                    f.write("(%s / %s) [FAIL] TOTAL for %s: %s%s\n\n" % (
                        self._left_pad(component.points_got),
                        self._left_pad(component.points_possible),
                        component.name, component.error,
                        ('\n' + component.error_verbose)
                        if component.error_verbose else ''))
                else:
                    component_pass = True

                    for part in component.parts:
                        if part.grade >= 1:
                            f.write("(%s / %s) [PASS] %s: %s\n" % (
                                self._left_pad(part.points_got),
                                self._left_pad(part.points_possible),
                                component.name, part.name))
                        else:
                            component_pass = False
                            assignment_pass = False
                            f.write("(%s / %s) [FAIL] %s: %s - %s\n" % (
                                self._left_pad(part.points_got),
                                self._left_pad(part.points_possible),
                                component.name, part.name, part.log))

                    # print totals for assignment component
                    f.write("(%s / %s) [%s] TOTAL for %s\n\n" % (
                        self._left_pad(component.points_got),
                        self._left_pad(component.points_possible),
                        "PASS" if component_pass else "FAIL",
                        component.name))

            # print totals for complete assignment
            f.write("(%s / %s) [%s] TOTAL for %s (without penalties)\n" % (
                self._left_pad(grade.raw_grade),
                self._left_pad(Fraction(1)),
                "PASS" if assignment_pass else "FAIL",
                self._assignment.name))

            # print penalties (like being late)
            for penalty in grade.penalties:
                if penalty.points_delta != 0:
                    f.write("(%s) Penalty: %s\n" % (
                        self._left_pad(penalty.points_delta),
                        penalty.name
                    ))

            f.write("\n-----------------------\n| %s%% FINAL SCORE "
                    "|\n-----------------------\n\n" %
                    (self._left_pad(grade.grade)))

            # write filenames and hashes
            file_hashes, submission_hash = self.generate_submission_hash()
            f.write("---- File Hashes ----\n")
            # x is file_path and y is file_path_str, not used
            for x, y, file_path_str_abbrev, file_hash in file_hashes:
                f.write("(sha1: %s) %s\n" % (file_hash, file_path_str_abbrev))
            f.write("\n---- Submission Hash ----\n(sha1: %s)\n\n"
                    % submission_hash)
            f.write('%s\n' % self.ZUCCHINI_END_GRADELOG)

        # write gradelog hash
        with open(gradelog_path, 'r+') as f:
            file_data = f.read()
            begin_idx = file_data.index(self.ZUCCHINI_BEGIN_GRADELOG)
            end_idx = file_data.index(self.ZUCCHINI_END_GRADELOG)
            gradelog_data = file_data[begin_idx:end_idx]
            gradelog_hash = hashlib.sha1(gradelog_data.encode()).hexdigest()
            f.write("%s\n" % (gradelog_hash))

    def generate_submission_hash(self):
        files = []

        # get all files in submission directory
        submission_files_path = self._submission.files_path
        for (dirpath, dirnames, filenames) in os.walk(submission_files_path):
            for file_name in filenames:
                file_path = os.path.join(dirpath, file_name)

                # reads in file in chunks and gets hash
                hasher = hashlib.sha1()
                with open(file_path, 'rb') as f:
                    file_chunk = f.read(self.READ_BUFFER_SIZE)
                    if not file_chunk:
                        break
                    hasher.update(file_chunk)
                file_hash = hasher.hexdigest()

                files.append(
                    (file_path, str(file_path), "abbreviated path", file_hash))

        if len(files) < 1:
            return [], hashlib.sha1(''.encode('utf-8')).hexdigest()

        common_path = str(os.path.commonpath([x[0] for x in files]))

        files2 = []
        for x in files:
            files2.append(self._files_tuple_mapper(common_path, x))

        files2.sort(key=lambda x: x[2])
        files = files2

        # get submission hash (hash of all file hashes, in order)
        submission_hasher = hashlib.sha1()
        for file_path, file_path_str, file_path_str_abbrv, file_hash in files:
            submission_hasher.update(file_hash.encode('utf-8'))
        submission_hash = submission_hasher.hexdigest()

        return files, submission_hash


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

            yield grade

    def grades(self):
        """Return a list of all grades"""

        for submission in self.submissions:
            yield Grade(self.assignment, submission)
