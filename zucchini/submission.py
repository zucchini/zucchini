import os
import json

from .grades import AssignmentComponentGrade
from .constants import SUBMISSION_META_FILE, SUBMISSION_FILES_DIRECTORY
from .utils import ConfigDictMixin, datetime_to_string, copy_globs, \
                   FileNotFoundError


class BrokenSubmissionError(Exception):
    def __init__(self, message, verbose=None):
        super(BrokenSubmissionError, self).__init__(message)
        self.message = message
        self.verbose = verbose


class Submission(ConfigDictMixin):
    def __init__(self, student_name, assignment, path, graded, id=None,
                 seconds_late=None, error=None, component_grades=None):
        self.student_name = student_name
        self.assignment = assignment
        self.path = path
        self.graded = graded
        self.id = id
        self.seconds_late = seconds_late

        if component_grades is not None and error is not None:
            raise ValueError('either specify component_grades or error, '
                             'but not both')

        self.error = error

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
            json.dump(meta, meta_file, sort_keys=True, indent=2,
                      separators=(',', ': '))

    def initialize_metadata(self):
        """Create initial meta.json"""

        self._write_meta_json()

    def is_broken(self):
        """
        Return true if this assignment has been graded but at least one
        component grade flagged a broken submisison.
        """

        return self.error is not None or self.component_grades is not None \
            and any(component.is_broken()
                    for component in self.component_grades)

    # XXX Support copying directories
    def copy_files(self, files, path, allow_fail=False):
        # type: (List[str], str, bool) -> None
        files_dir = os.path.join(self.path, SUBMISSION_FILES_DIRECTORY)

        try:
            copy_globs(files, files_dir, path)
        except FileNotFoundError as err:
            if not allow_fail:
                raise BrokenSubmissionError(str(err))

    def write_grade(self, component_grades):  # (Dict[object, object]) -> None
        """
        Set the component grades to `component_grades' and write the
        new submission metadata to the metadata file.
        """

        self.graded = True
        self.error = None
        self.component_grades = component_grades
        self._write_meta_json()
