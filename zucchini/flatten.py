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


class ArchiveError(Exception):
    """Raised for corrupt archives"""
    pass


class Archive:
    """Handle an archive format for the extraction code"""

    __metaclass__ = ABCMeta

    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.open()

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def path(self):
        """Return the path to this archive"""
        return self.path

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
        try:
            self.archive = tarfile.open(self.path)
        except tarfile.TarError as err:
            raise ArchiveError(err)

    def close(self):
        try:
            self.archive.close()
        except tarfile.TarError as err:
            raise ArchiveError(err)

    def uncompressed_size(self):
        try:
            return sum(member.size for member in self.archive.getmembers())
        except tarfile.TarError as err:
            raise ArchiveError(err)

    def names(self):
        try:
            return [member.name for member in self.archive.getmembers()
                    if member.isfile()]
        except tarfile.TarError as err:
            raise ArchiveError(err)

    def file(self, name):
        try:
            return self.archive.extractfile(name)
        except tarfile.TarError as err:
            raise ArchiveError(err)


class ZipArchive(Archive):
    def open(self):
        try:
            self.archive = zipfile.ZipFile(self.path)
        except zipfile.BadZipfile as err:
            raise ArchiveError(err)

    def close(self):
        try:
            self.archive.close()
        except zipfile.BadZipfile as err:
            raise ArchiveError(err)

    def uncompressed_size(self):
        try:
            return sum(info.file_size for info in self.archive.infolist())
        except zipfile.BadZipfile as err:
            raise ArchiveError(err)

    def names(self):
        try:
            return [info.filename for info in self.archive.infolist()
                    if info.filename and info.filename[-1] != '/']
        except zipfile.BadZipfile as err:
            raise ArchiveError(err)

    def file(self, name):
        try:
            return self.archive.open(name)
        except zipfile.BadZipfile as err:
            raise ArchiveError(err)


# To protect against zipbombs, refuse to extract if archive contents are
# larger than 64 MiB. This may need adjusting if students try to upload
# 300 MiB pictures of Diddy for their gba games
MAX_UNCOMPRESSED_SIZE_BYTES = 64 * 2**20

ARCHIVE_TYPES = {
    '.tgz': TarArchive,
    '.tar.gz': TarArchive,
    '.tar.bz2': TarArchive,
    '.tbz2': TarArchive,
    '.tar.xz': TarArchive,
    '.txz': TarArchive,
    '.zip': ZipArchive,
}


def extract(archive, dest_dir, max_archive_size=None):
    """
    Extract Archive to X, flattening it as needed
    """

    if max_archive_size is None:
        max_archive_size = MAX_UNCOMPRESSED_SIZE_BYTES

    with archive:
        # Don't do zipbomb detection if the user switches it off by
        # passing a max size <= 0
        if max_archive_size > 0:
            uncompressed_size = archive.uncompressed_size()
            if uncompressed_size > max_archive_size:
                # In case this error bubbles its way up to students,
                # don't reveal the setup of their filesystem
                safe_archive_name = os.path.basename(archive.path())
                raise ArchiveError("Archive `{}' has uncompressed size of {} "
                                   "bytes which exceeds maximum of {} bytes. "
                                   "Refusing to extract!"
                                   .format(safe_archive_name,
                                           uncompressed_size,
                                           max_archive_size))

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
                if len(prefix) >= len(component) \
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


def flatten(files_dir, max_archive_size=None):
    """
    Search the top-level files in `files_dir' for archives, and extract
    each one. Check for zipbombs.
    """

    for file_ in os.listdir(files_dir):
        for extension, archive_cls in ARCHIVE_TYPES.items():
            if file_.lower().endswith(extension):
                archive_path = os.path.join(files_dir, file_)
                extract(archive_cls(archive_path), files_dir, max_archive_size)
                # There's not much use wasting disk space by keeping
                # the archive around now that we've extracted it, so
                # delete it.
                os.remove(archive_path)
                break
