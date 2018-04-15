import os
import re
import shutil
from zipfile import ZipFile

from ..utils import sanitize_path, mkdir_p


class CanvasArchiveLoader(object):
    FILENAME_REGEX = re.compile(r'^(?P<user_name>[a-z\-_]+)(?P<user_id>\d+)_'
                                r'question_\d+_\d+_(?P<filename>.+)$')

    def __init__(self, zipfile_path):
        self.zipfile_path = zipfile_path
        self.zipfile = None
        # Map from student id to list of (zip_filename, original_filename)
        self.submissions = {}

    def __enter__(self):
        self.zipfile = ZipFile(self.zipfile_path)
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.zipfile.close()

    def has_submission(self, user_id):
        return user_id in self.submissions

    def load(self):
        for filename in self.zipfile.namelist():
            match = self.FILENAME_REGEX.match(filename)
            if match is None:
                raise Exception('filename in archive in invalid format')
            self.submissions.setdefault(int(match.group('user_id')), []) \
                .append((filename, match.group('filename')))

    def extract_files(self, user_id, dest_dir):
        for zip_filename, filename in self.submissions.get(user_id, []):
            fullpath = os.path.join(dest_dir, sanitize_path(filename))
            mkdir_p(os.path.dirname(fullpath))

            with self.zipfile.open(zip_filename) as sourcefile, \
                    open(fullpath, 'wb') as destfile:
                shutil.copyfileobj(sourcefile, destfile)
