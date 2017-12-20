import os

import yaml

from .constants import GRADE_LOG_FILE


class Submission(object):
    def __init__(self, assignment, path):
        self.assignment = assignment
        self.path = path

        # TODO: Validate the path - make sure everything that's needed for the
        # assignment is available in the path

    def copy_files(self, files, path):  # (List[str], str) -> None
        """Copy the assignment files in the files list to the new path"""
        # TODO: Implement this - we need some sort of glob call here
        # TODO: How to make it safe?

        pass

    def write_grade(self, grade_data):  # (Dict[object, object]) -> None
        """Write the grade_data dictionary to the log file"""

        with open(os.path.join(self.path, GRADE_LOG_FILE)) as grade_file:
            yaml.safe_dump(grade_data, grade_file)
