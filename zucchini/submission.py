import os
import json
from datetime import datetime

from .grades import AssignmentComponentGrade
from .constants import SUBMISSION_META_FILE, SUBMISSION_FILES_DIRECTORY
from .utils import ConfigDictMixin, datetime_from_string, \
                   datetime_to_string, copy_globs, FileNotFoundError


class BrokenSubmissionError(Exception):
    pass


class Submission(ConfigDictMixin):
    def __init__(self, student_name, assignment, path, graded, id=None,
                 submission_time=None, component_grades=None):
        self.student_name = student_name
        self.assignment = assignment
        self.path = path
        self.graded = graded
        self.id = id

        if isinstance(submission_time, datetime):
            self.submission_time = submission_time
        else:
            self.submission_time = datetime_from_string(submission_time)

        if component_grades is None:
            self.component_grades = None
        else:
            self.component_grades = [
                AssignmentComponentGrade.from_config_dict(grade_dict)
                for grade_dict in component_grades]

        # TODO: Validate the path - make sure everything that's needed for the
        # assignment is available in the path

    @classmethod
    def load_from_dir(cls, assignment, path):
        """Load a Submission instance from a submission directory."""

        metadata_path = os.path.join(path, SUBMISSION_META_FILE)

        with open(metadata_path) as meta_file:
            meta_json = json.load(meta_file)

        return cls.from_config_dict(meta_json, assignment=assignment,
                                    path=path)

    def _meta_json(self):
        """Return a json representation of this instance"""

        meta = self.to_config_dict('assignment', 'path')
        if 'submission-time' in meta:
            meta['submission-time'] = datetime_to_string(self.submission_time)

        return meta

    def _write_meta_json(self):
        """Json-ify this instance and write to the metadata json file"""

        meta = self._meta_json()

        metadata_path = os.path.join(self.path, SUBMISSION_META_FILE)
        with open(metadata_path, 'w') as meta_file:
            json.dump(meta, meta_file)

    def initialize_metadata(self):
        """Create initial meta.json"""

        self._write_meta_json()

    # XXX Support copying directories
    def copy_files(self, files, path):  # (List[str], str) -> None
        files_dir = os.path.join(self.path, SUBMISSION_FILES_DIRECTORY)

        try:
            copy_globs(files, files_dir, path)
        except FileNotFoundError as err:
            raise BrokenSubmissionError(str(err))

    def write_grade(self, component_grades):  # (Dict[object, object]) -> None
        """
        Set the component grades to `component_grades' and write the
        new submission metadata to the metadata file.
        """

        self.graded = True
        self.component_grades = component_grades
        self._write_meta_json()
