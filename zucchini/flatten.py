"""Flatten a submission like the old SubmissionFix script"""

import os
import tarfile
import posixpath
import shutil
import zipfile
from abc import ABCMeta, abstractmethod

from .utils import mkdir_p, sanitize_path

# XXX Slow because unlike Marie's SubmissionFix script, does not use
#     native extractors
# XXX Does not support symlinks properly. Ignores them in tar archives
#     and writes out their destination in zip archives
# XXX Does not support empty directories
# XXX No error handling


class Archive:
    """Handle an archive format for the extraction code"""

    __metaclass__ = ABCMeta

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @abstractmethod
    def open(self):
        """
        Open the archive at self.path and store it somewhere like
        self.archive.
        """
        pass

    @abstractmethod
    def close(self):
        """Close archive"""
        pass

    @abstractmethod
    def uncompressed_size(self):
        """
        Return the total size of all the files in the archive in bytes.
        """
        pass

    @abstractmethod
    def names(self):
        """Return a list of filenames in this archive."""
        pass

    @abstractmethod
    def file(self, name):
        """Return a file-like object pointing to name"""
        pass


class TarArchive(Archive):
    def open(self):
        self.archive = tarfile.open(self.path)

    def close(self):
        self.archive.close()

    def uncompressed_size(self):
        return sum(member.size for member in self.archive.getmembers())

    def names(self):
        return [member.name for member in self.archive.getmembers()
                if member.isfile()]

    def file(self, name):
        return self.archive.extractfile(name)


class ZipArchive(Archive):
    def open(self):
        self.archive = zipfile.ZipFile(self.path)

    def close(self):
        self.archive.close()

    def uncompressed_size(self):
        return sum(info.file_size for info in self.archive.infolist())

    def names(self):
        return [info.filename for info in self.archive.infolist()
                if info.filename and info.filename[-1] != '/']

    def file(self, name):
        return self.archive.open(name)


# To protect against zipbombs, refuse to extract if archive contents are
# larger than 10 MiB. This may need adjusting if students try to upload
# 300 MiB pictures of Diddy for their gba games
MAX_UNCOMPRESSED_SIZE_BYTES = 10 * 2**20

ARCHIVE_TYPES = {
    '.tgz': TarArchive,
    '.tar.gz': TarArchive,
    '.tar.bz2': TarArchive,
    '.tbz2': TarArchive,
    '.tar.xz': TarArchive,
    '.txz': TarArchive,
    '.zip': ZipArchive,
}


def extract(archive, dest_dir):
    """
    Extract Archive to X, flattening it as needed
    """

    with archive:
        uncompressed_size = archive.uncompressed_size()
        if uncompressed_size > MAX_UNCOMPRESSED_SIZE_BYTES:
            raise ValueError('Archive uncompressed size of {} bytes '
                             'exceeds maximum of {} bytes. Refusing to '
                             'extract!'
                             .format(uncompressed_size,
                                     MAX_UNCOMPRESSED_SIZE_BYTES))

        names = {}

        for name in archive.names():
            # Remove backslash memes from malformed zip files
            safe_name = name.replace('\\', '/')
            components = sanitize_path(safe_name, path_lib=posixpath,
                                       join=False)

            if '__MACOSX' in components:
                # Skip macOS "Resource Forks"
                continue
            elif not components:
                # Empty filename
                continue

            names[name] = components

        if not names:
            # Empty archive!
            return

        prefix = next(iter(names.values()))

        # Try to find a prefix
        while prefix:
            for component in names.values():
                if len(prefix) > len(component) \
                        or component[:len(prefix)] != prefix:
                    break
            else:
                # Cool, we found the prefix!
                break

            prefix = prefix[:-1]

        # Strip prefix
        if prefix:
            for name in names:
                names[name] = names[name][len(prefix):]

        # Extract files
        for name in names:
            dirname = os.path.join(dest_dir, *names[name][:-1])
            basename = names[name][-1]

            mkdir_p(dirname)
            with open(os.path.join(dirname, basename), 'wb') as extracted, \
                    archive.file(name) as archived:
                shutil.copyfileobj(archived, extracted)


def flatten(files_dir):
    """
    Search the top-level files in `files_dir' for archives, and extract
    each one. Check for zipbombs.
    """

    for file_ in os.listdir(files_dir):
        for extension, archive_cls in ARCHIVE_TYPES.items():
            if file_.lower().endswith(extension):
                extract(archive_cls(os.path.join(files_dir, file_)), files_dir)
                break
