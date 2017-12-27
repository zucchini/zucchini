import os
import shutil
import tempfile

import click
import git
import yaml

from .graders import AVAILABLE_GRADERS
from .constants import ASSIGNMENT_CONFIG_FILE
from .utils import FromConfigDictMixin


class AssignmentComponent(FromConfigDictMixin):
    def __init__(self, assignment, name, backend, weight, files=None,
                 grader_files=None, backend_options=None):
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
        if self.files is not None and not isinstance(self.files, list):
            raise ValueError('List of files must be a list')

        self.grader_files = grader_files
        # TODO: Confirm that all of the files in the grading list exist

        # We then initialize the grader
        self.grader = backend_class.from_config_dict(backend_options)

    def grade_for_submission(self, submission):
        grading_directory = tempfile.mkdtemp('zucchini-component-')

        try:
            # Copy the submission first and the grading later so that if a file
            # exists in both, the grading copy overwrites the submission copy
            submission.copy_files(self.files, grading_directory)
            self.assignment.copy_files(self.grader_files, grading_directory)
            percent = self.grader.grade(submission, grading_directory)
        finally:
            shutil.rmtree(grading_directory)

        return percent * self.weight


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

        self.total_weight = sum(x.weight for x in self.components)

        # TODO: Handle assignments with no components or with 0 total weight

    def copy_files(self, files, path):  # (List[str], str) -> None
        """Copy the grader files in the files list to the new path"""
        # TODO: Implement this - we need some sort of glob call here
        # TODO: How to make it safe?

        pass

    def grade_for_submission(self, submission):
        # Return a tuple (earned_points, max_points)
        earned_score = 0
        for component in self.components:
            earned_score += component.grade_for_submission(submission)

        submission.write_grade({'earned': earned_score,
                                'out_of': self.total_weight})
        # TODO: Obviously a placeholder. We need to do a better implementation

        # TODO: We probably want to log, too
