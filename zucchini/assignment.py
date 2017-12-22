import os
import shutil

import click
import git
import yaml

from .graders import GraderInterface
from .constants import ASSIGNMENT_CONFIG_FILE

AVAILABLE_GRADERS = {cls.__name__: cls for cls in
                     GraderInterface.__subclasses__()}


class AssignmentComponent(object):
    def __init__(self, assignment, name, backend, weight, files, grader_files,
                 backend_options):
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
        # TODO: Confirm that the files input is a list

        self.grader_files = grader_files
        # TODO: Confirm that all of the files in the grading list exist

        # We then initialize the grader
        self.grader = backend_class(**backend_options)

    def prepare_submission_for_grading(self, submission):
        grading_directory = None  # TODO: WHERE DO WE STORE TEMP GRADING?

        # Copy the submission first and the grading later so that if a file
        # exists in both, the grading copy overwrites the submission copy
        submission.copy_files(self.files, grading_directory)
        self.assignment.copy_files(self.grader_files, grading_directory)

        return grading_directory

    def tear_down_graded_submission(self, grading_directory):
        shutil.rmtree(grading_directory)

    def grade_for_submission(self, submission):
        tmp_dir = self.prepare_submission_for_grading(submission)
        score = self.grader.grade(submission, tmp_dir) * self.weight
        self.tear_down_graded_submission(tmp_dir)

        return score


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

            # TODO: How do we handle config about the assignment's existence on
            # LMS platforms? Like the canvas: config?
        except KeyError as e:
            raise ValueError("Missing field in assignment config: %s" %
                             e.args[0])

        self.components = []

        # Now load the components (this is the fun part!)
        for component_config in config['components']:
            component = AssignmentComponent(assignment=self,
                                            **component_config)
            self.components.append(component)

            # TODO: This URGENTLY needs error handling.

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
