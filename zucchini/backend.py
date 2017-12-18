import os
import subprocess
import sys
import yaml


class BackendError(Exception):
    pass


class InvalidBackendError(BackendError):
    pass


class Backend:
    """Handle a student submission"""

    def __init__(self, files=None, grader_files=None):
        self.files = files or ()
        self.grader_files = grader_files or ()

    @staticmethod
    def need_tmpdir(self):
        """
        Return True if this backend needs a temporary directory, else False.
        """
        return False

    def run(self, directory, options=None):
        """Handle student code and return a Grade instance."""
        pass


class OpenFileBackend(Backend):
    """Open all the files in files"""

    def run(self, directory, options=None):
        if not self.files:
            raise BackendError('No files to open!')

        for file_ in self.files:
            path = os.path.join(directory, file_)

            if sys.platform.startswith('win'):
                os.startfile(path)
            elif sys.platform.startswith('linux'):
                subprocess.run(['xdg-open', path])
            elif sys.platform.startswith('darwin'):
                subprocess.run(['open', path])
            else:
                raise BackendError("I don't know how to open files on "
                                   "platform `{}'!".format(sys.platform))


class BackendRunner:
    """
    Run a submission through a backend, reading its options from
    backend-options.yml if possible.
    """

    BACKEND_CLASSES = {
        'open-file': OpenFileBackend,
    }

    def __init__(self, backend_name, files, grader_files):
        if backend_name not in self.BACKEND_CLASSES:
            raise InvalidBackendError()

        self.files = files
        self.grader_files = grader_files

        backend_class = self.BACKEND_CLASSES[backend_name]
        self.backend = backend_class(files=self.files,
                                     grader_files=self.grader_files)

    def run(self, directory):
        try:
            with open(os.path.join(directory, 'backend-options.yml')) as f:
                backend_options = yaml.safe_load(f)
        except FileNotFoundError:
            backend_options = {}

        self.backend.run(directory, backend_options)
