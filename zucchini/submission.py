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
    def __init__(self, student_name, assignment, metadata_path, files_path,
                 graded, id=None, seconds_late=None, error=None,
                 component_grades=None):
        self.student_name = student_name
        self.assignment = assignment
        self.metadata_path = metadata_path
        self.files_path = files_path
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

    @staticmethod
    def get_paths(path):
        """
        Calculate the metadata and files paths for a standard submission
        from `zucc load'.
        """
        metadata_path = os.path.join(path, SUBMISSION_META_FILE)
        files_path = os.path.join(path, SUBMISSION_FILES_DIRECTORY)

        return metadata_path, files_path

    @classmethod
    def load_from_empty_dir(cls, assignment, path, **kwargs):
        """
        Load a Submission instance from an uninitialized submission directory.
        """

        metadata_path, files_path = cls.get_paths(path)
        return cls(assignment=assignment, metadata_path=metadata_path,
                   files_path=files_path, **kwargs)

    @classmethod
    def load_from_dir(cls, assignment, path):
        """Load a Submission instance from a submission directory."""

        metadata_path, files_path = cls.get_paths(path)

        with open(metadata_path) as meta_file:
            meta_json = json.load(meta_file)

        return cls.from_config_dict(meta_json, assignment=assignment,
                                    metadata_path=metadata_path,
                                    files_path=files_path)

    @classmethod
    def load_from_raw_files(cls, assignment, files_path):
        return Submission(student_name='', assignment=assignment,
                          metadata_path=None, files_path=files_path,
                          graded=False)

    @classmethod
    def load_from_component_grades_json(cls, assignment, component_grades_fp,
                                        seconds_late=None):
        component_grades = json.load(component_grades_fp)

        return Submission(student_name='', assignment=assignment,
                          metadata_path=None, files_path=None, graded=True,
                          seconds_late=seconds_late,
                          component_grades=component_grades)

    def _meta_json(self):
        """Return a json representation of this instance"""

        meta = self.to_config_dict('assignment', 'metadata_path', 'files_path')
        if 'submission-time' in meta:
            meta['submission-time'] = datetime_to_string(self.submission_time)

        return meta

    def _write_meta_json(self):
        """Json-ify this instance and write to the metadata json file"""

        meta = self._meta_json()

        with open(self.metadata_path, 'w') as meta_file:
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
        try:
            copy_globs(files, self.files_path, path)
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
