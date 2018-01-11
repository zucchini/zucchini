"""Flatten a submission like the old SubmissionFix script"""

import os
import tarfile
import posixpath
import shutil
import zipfile
from collections import namedtuple
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


ParsedCanvasSuffix = namedtuple('ParsedCanvasSuffix', ('unbroken_filename',
                                                       'version', 'filename'))


def canvas_parse_suffix(filename):
    """
    Extract the actual name and version of a filename afflicted by the
    Canvas suffix scheme hand-crafted by UGA engineers. Returns a
    ParsedCanvasSuffix tuple of the submitted filename, the version, and
    the actual filename.
    """

    version = 0
    unbroken_filename = filename

    splat = filename.rsplit('.', 1)
    if len(splat) == 2:
        lhs, ext = splat
        splat = lhs.rsplit('-', 1)
        if len(splat) == 2:
            basename, suffix = splat
            try:
                version_parsed = int(suffix)
            except ValueError:
                pass
            else:
                if version_parsed > 0:
                    version = version_parsed
                    unbroken_filename = '{}.{}'.format(basename, ext)

    return ParsedCanvasSuffix(unbroken_filename, version, filename)


def canvas_desuffix(files_dir):
    """
    Fix Canvas -1 -2 -3 suffixes as described in the flatten()
    docstring. Take the most naive approach possible:
    in spite of possible consequences, take the most recent file
    version: take bob-3.txt over bob-2.txt, etc.
    """

    # First, parse all the suffixes in the filenames and sort them by
    # version. This way, we will remove earlier versions before they've
    # been replaced. (If we didn't do this, we might move bob-3.txt to
    # bob.txt, and then later remove bob.txt -- the copy we want to keep!)
    filenames = sorted((canvas_parse_suffix(file_)
                        for file_ in os.listdir(files_dir)),
                       key=lambda parsed: parsed.version)

    # Do a first pass to put the 'newest' of each suffixed file in this
    # dictionary
    newest_versions = {}

    for unbroken_filename, version, _ in filenames:
        if newest_versions.get(unbroken_filename, -1) < version:
            newest_versions[unbroken_filename] = version

    # Now, rename newer versions and delete old ones
    for unbroken_filename, version, original_filename in filenames:
        current_path = os.path.join(files_dir, original_filename)

        if newest_versions[unbroken_filename] == version:
            if unbroken_filename != original_filename:
                new_path = os.path.join(files_dir, unbroken_filename)
                os.rename(current_path, new_path)
        else:
            # Remove pointless outdated file
            os.remove(current_path)


def flatten(files_dir, remove_canvas_suffixes=True):
    """
    Search the top-level files in `files_dir' for archives, and extract
    each one. Check for zipbombs.

    If `remove_canvas_suffixes' is True (default True), remove the `-n'
    suffixes from all files in the submission. For example, if a student
    re-submits mycircuit.sim, Canvas will rename it to mycircuit-1.sim,
    and after another re-submission, mycircuit-2.sim and so on. This
    breaks a lot of things!
    """

    # Remove -1 -2 -3 canvas suffixes before looking for archives so we
    # don't mess up the file extension archive type auto-detection
    # (e.g., it wouldn't understand a .tar-1.gz file).
    if remove_canvas_suffixes:
        canvas_desuffix(files_dir)

    # Extract archives
    for file_ in os.listdir(files_dir):
        for extension, archive_cls in ARCHIVE_TYPES.items():
            if file_.lower().endswith(extension):
                extract(archive_cls(os.path.join(files_dir, file_)), files_dir)
                break
