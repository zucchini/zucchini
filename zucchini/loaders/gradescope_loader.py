import os
import yaml
import shutil
from zipfile import ZipFile

from ..utils import sanitize_path, mkdir_p

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader


class GradescopeLoader(object):
    def __init__(self, zipfile_path):
        self.zipfile_path = zipfile_path
        self.zipfile = None
        self.rootdir = None
        self.submissions = {}

    def __enter__(self):
        self.zipfile = ZipFile(self.zipfile_path)
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.zipfile.close()

    def load(self):
        # Gradescope was designed by Bay Area folks
        self.rootdir = self.zipfile.namelist()[0].split('/', maxsplit=1)[0]
        with self.zipfile.open('{}/submission_metadata.yml'
                               .format(self.rootdir)) as metadata:
            meta = yaml.load(metadata, Loader=SafeLoader)

        self.submissions = {submission_id: data[':submitters'][0][':name']
                            for submission_id, data in meta.items()}

    def extract_files(self, submission_id, dest_dir):
        prefix = '{}/{}/'.format(self.rootdir, submission_id)

        for name in self.zipfile.namelist():
            if not name.startswith(prefix) or name.endswith('/'):
                continue

            basename = sanitize_path(name[len(prefix):])
            fullpath = os.path.join(dest_dir, basename)
            mkdir_p(os.path.dirname(fullpath))

            with self.zipfile.open(name) as sourcefile, \
                    open(fullpath, 'wb') as destfile:
                shutil.copyfileobj(sourcefile, destfile)
