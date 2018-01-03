import os
import shutil
import tempfile
from fractions import Fraction
from collections import namedtuple

import click
import git
import yaml

from .grades import AssignmentComponentGrade
from .graders import AVAILABLE_GRADERS
from .constants import ASSIGNMENT_CONFIG_FILE, ASSIGNMENT_FILES_DIRECTORY
from .utils import ConfigDictMixin, copy_globs, sanitize_path


ComponentPart = namedtuple('ComponentPart', ('weight', 'part'))


class AssignmentComponent(ConfigDictMixin):
    def __init__(self, assignment, name, backend, weight, parts, files=None,
                 grading_files=None, backend_options=None):
        self.assignment = assignment
        self.name = name

        # Get the backend class
        if backend not in AVAILABLE_GRADERS:
            raise ValueError("Invalid backend: %s" % backend)

        backend_class = AVAILABLE_GRADERS[backend]

        self.weight = weight
        if type(self.weight) != int:
            raise ValueError("Component weights need to be integers.")

        self.files = files
        if self.files is not None:
            if not isinstance(self.files, list):
                raise ValueError('List of files must be a list')
            else:
                self.files = [sanitize_path(file_) for file_ in self.files]

        # TODO: Confirm that all of the files in the grading list exist
        self.grading_files = grading_files
        if self.grading_files is not None:
            if not isinstance(self.grading_files, list):
                raise ValueError('List of grading files must be a list')
            else:
                self.grading_files = [sanitize_path(file_)
                                      for file_ in self.grading_files]

        # We then initialize the grader
        self.grader = backend_class.from_config_dict(backend_options or {})
        self.parts = []

        for part_dict in parts:
            if 'weight' not in part_dict:
                raise ValueError('every part needs a weight!')
            else:
                weight = part_dict['weight']
                del part_dict['weight']
            part = self.grader.part_from_config_dict(part_dict)
            self.parts.append(ComponentPart(weight=weight, part=part))

    def grade_submission(self, submission):
        grading_directory = tempfile.mkdtemp(prefix='zucchini-component-')

        try:
            # Copy the submission first and the grading later so that if a file
            # exists in both, the grading copy overwrites the submission copy
            if self.files:
                submission.copy_files(self.files, grading_directory)
            if self.grading_files:
                self.assignment.copy_files(self.grading_files,
                                           grading_directory)
            # self.parts is a list of (weight, Part) tuples, but we only
            # wanna pass Part instances to the grader
            parts = [part.part for part in self.parts]
            part_grades = self.grader.grade(submission, grading_directory,
                                            parts)
        finally:
            shutil.rmtree(grading_directory)

        return AssignmentComponentGrade(part_grades)

    def calculate_grade(self, component_grade):
        # type: (AssignmentComponentGrade) -> fractions.Fraction
        return component_grade.calculate_grade(self.parts)


# This class contains the Assignment configuration for the local file
class Assignment(object):
    def __init__(self, root):
        self.root = root

        # Confirm the presence of a git repo here
        try:
            self.repo = git.Repo(self.root)
        except git.exc.InvalidGitRepositoryError:
            raise ValueError("This directory is not a valid git repository.")

        config_file_path = os.path.join(self.root, ASSIGNMENT_CONFIG_FILE)

        if not os.path.exists(config_file_path):
            raise ValueError("This directory is not a valid Zucchini "
                             "assignment: the Zucchini config is missing.")

        with click.open_file(config_file_path, 'r') as config_file:
            config = yaml.safe_load(config_file)

        if config is None:
            raise ValueError("The assignment configuration file could not be "
                             "parsed.")

        try:
            # Get the assignment's name, author
            self.name = config['name']
            self.author = config['author']
        except KeyError as e:
            raise ValueError("Missing field in assignment config: %s" %
                             e.args[0])

        # TODO: Don't hardcode Canvas logic in here. Need to make something
        #       like "Modules" for handling these things.
        if 'canvas' in config:
            try:
                self.canvas_course_id = int(config['canvas']['course-id'])
                self.canvas_assignment_id = \
                    int(config['canvas']['assignment-id'])
            except KeyError as err:
                raise ValueError('canvas section in assignment config is '
                                 'missing key: {}'.format(err.args[0]))
            except ValueError as err:
                raise ValueError('canvas id is not an integer: {}'
                                 .format(str(err)))
        else:
            self.canvas_course_id = None
            self.canvas_assignment_id = None

        self.components = []

        # Now load the components (this is the fun part!)
        for component_config in config['components']:
            component = AssignmentComponent.from_config_dict(component_config,
                                                             assignment=self)
            self.components.append(component)

        if len({component.name for component in self.components}) \
                != len(self.components):
            raise ValueError('Duplicate component names')

        self.total_weight = sum(c.weight for c in self.components)

        # TODO: Handle assignments with no components or with 0 total weight

    def copy_files(self, files, path):  # (List[str], str) -> None
        """Copy the grader files in the files list to the new path"""

        grading_files_dir = os.path.join(self.root, ASSIGNMENT_FILES_DIRECTORY)
        # XXX Replace FileNotFoundError raised with a better exception
        copy_globs(files, grading_files_dir, path)

    def grade_submission(self, submission):
        # type: (Submission) -> List[AssignmentComponentGrade]
        """
        Grade each assignment component of submission, returning an
        AssignmentComponentGrade for each component.
        """

        # The grading data for each part (individual test) of each
        # component (test suite) of this assignment
        grades = [component.grade_submission(submission)
                  for component in self.components]
        return grades
        # TODO: We probably want to log, too

    def calculate_grade(self, component_grades):
        # type: (List[AssignmentComponentGrade] -> fractions.Fraction
        """
        Calculate the final grade for a submission given the list of
        AssignmentComponentGrades for the submission.
        """
        total_possible = sum(component.weight for component in self.components)
        total_earned = sum(component.calculate_grade(grade) * component.weight
                           for grade, component
                           in zip(component_grades, self.components))

        return Fraction(total_earned, total_possible)
