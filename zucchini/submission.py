import os
import json

from .constants import SUBMISSION_META_FILE, SUBMISSION_FILES_DIRECTORY
from .utils import FromConfigDictMixin, datetime_from_string, \
                   datetime_to_string, copy_globs


class BrokenSubmissionError(Exception):
    pass


class Submission(FromConfigDictMixin):
    def __init__(self, assignment, path, id=None, submission_time=None,
                 grading=None):
        self.assignment = assignment
        self.path = path
        self.id = id

        if isinstance(submission_time, str):
            self.submission_time = datetime_from_string(submission_time)
        else:
            self.submission_time = submission_time

        self.grading = grading

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

        meta = {}
        if id is not None:
            meta['id'] = self.id
        if self.submission_time is not None:
            meta['submission-time'] = datetime_to_string(self.submission_time)
        if self.grading is not None:
            meta['grading'] = self.grading

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

    def write_grade(self, grade_data):  # (Dict[object, object]) -> None
        """Write the grade_data dictionary to the metadata file"""

        self.grading = grade_data
        self._write_meta_json()
