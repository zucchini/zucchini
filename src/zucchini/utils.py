from pathlib import Path
import shlex
from typing import Annotated, TypeAlias
import arrow
import datetime as dt
import inspect
import os
import shutil
import subprocess

from pydantic import BeforeValidator

def recursive_get_using_string(collection, key: str):
    """
    Given a collection and a key in the format of x.y.z.a, 
    return collection[x][y][z][a].
    """
    item = collection
    for k in key.split("."):
        if k.isdigit():
            k = int(k)
        item = item[k]
    
    return item

# TODO: remove all of these
PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT
TimeoutExpired = subprocess.TimeoutExpired
CompletedProcess = subprocess.CompletedProcess
run_process = subprocess.run

def _as_shlex_cmd(s: str | list[str]) -> list[str]:
    if isinstance(s, list):
        return s
    return shlex.split(s)
ShlexCommand: TypeAlias = Annotated[list[str], BeforeValidator(_as_shlex_cmd)]
"""
Pydantic validator which accepts strings (and lists of strings) which act as script commands,
and exposes the field as a split script command (as if from `shlex.split`).
"""

# TODO: evaluate need for sanitize_path
def sanitize_path(path, path_lib=os.path, join=True):
    """
    Convert an untrusted path to a relative path.

    Defaults to using os.path to manipulate (native) paths, but you can
    pass path_lib=posixpath to always use Unix paths, for example.

    If `join=False', return a list of path components. Default (True) is
    to path_lib.join() them.
    """

    # Remove intermediate ..s
    path = path_lib.normpath(path)
    # Remove leading /s
    path = path.lstrip(path_lib.sep)
    components = path.split(path_lib.sep)

    # Remove leading ..s and DOS drive letters
    while components and (components[0] == '..' or
                          len(components[0]) == 2 and components[0][1] == ':'):
        components = components[1:]

    if join:
        return path_lib.join(*components)
    else:
        return components

def copy_globs(globs: list[str], src_dir: os.PathLike[str], dest_dir: os.PathLike[str]):
    """
    Copy files matched by `globs` (a list of glob strings) from src_dir
    to dest_dir, maintaining directories if possible.
    """

    src_dir = Path(src_dir)
    dest_dir = Path(dest_dir)
    files_to_copy: list[Path] = []

    # Do a first pass to check for missing files. This way, we don't
    # copy a bunch of files only to blow up when we can't find a
    # later file.
    for file_glob in globs:
        old_len = len(files_to_copy)
        files_to_copy += src_dir.glob(file_glob)

        if len(files_to_copy) - old_len == 0: # No new files were added
            raise FileNotFoundError(f"missing file {file_glob!r}")

    for src_file in files_to_copy:
        rel_path = src_file.relative_to(src_dir)
        dest = dest_dir / rel_path

        if src_file.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src_file, dest)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(src_file, dest)


# Same as the Canvas date format
_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

def datetime_from_string(date_str: str) -> dt.datetime:
    """
    Convert a human-readable date/time string (in the format used by
    Canvas and in submission metadata files) to a datetime instance.
    """

    return arrow.get(date_str).to('utc').datetime

def datetime_to_string(datetime_obj: dt.datetime) -> str:
    """Convert a datetime UTC instance to a human-readable date/time string."""
    return datetime_obj.strftime(_DATETIME_FORMAT)

class ConfigDictMixin(object):
    @staticmethod
    def _to_field(config_key):
        """Convert a config key to a field name"""
        return config_key.replace('-', '_')

    @staticmethod
    def _to_config(field_name):
        """Convert a field name to a config key"""
        return field_name.replace('_', '-')

    @classmethod
    def _find_args(cls, exclude_args):
        """
        Find the required and optional arguments of the constructor for
        the class `cls'. Returns a tuple containing two lists: the first
        contains required args; the second contains optional args.

        Exclude arguments found in `exclude_args'.
        """

        arg_spec = inspect.getfullargspec(cls.__init__)
        num_optional_args = 0 if arg_spec.defaults is None \
            else min(len(arg_spec.args)-1, len(arg_spec.defaults))
        first_optional_arg = len(arg_spec.args) - num_optional_args

        required_args = [arg for arg in arg_spec.args[1:first_optional_arg]
                         if arg not in exclude_args]
        optional_args = [arg for arg in arg_spec.args[first_optional_arg:]
                         if arg not in exclude_args]

        return required_args, optional_args

    def to_config_dict(self, *exclude):
        """
        Try to convert an instance to a configuration dictionary by
        accessing fields named after constructor fields.
        """

        required_args, optional_args = self._find_args(exclude)
        result = {}

        for arg in required_args:
            result[self._to_config(arg)] = getattr(self, arg)

        for arg in optional_args:
            if hasattr(self, arg) and getattr(self, arg) is not None:
                result[self._to_config(arg)] = getattr(self, arg)

        return result

    @classmethod
    def from_config_dict(cls, config_dict, **extra_kwargs):
        """
        Convert a dictionary, checking for invalid keys, that can be
        safely passed as kwargs. Checks only for the presence of options
        (keys), not their types. Converts dashes to underscores in
        option names.

        Considers optional arguments to cls.__init__() optional options,
        and required arguments to cls.__init__() required options.
        Rejects options also found in extra_kwargs.
        """

        # If already deserialized, just return
        if isinstance(config_dict, cls):
            return config_dict

        required_args, optional_args = cls._find_args(extra_kwargs)

        kwargs = {}

        for raw_key in config_dict:
            key = cls._to_field(raw_key)

            if key not in required_args + optional_args:
                raise ValueError("Unknown config key `{}'".format(raw_key))

            kwargs[key] = config_dict[raw_key]

        for key in required_args:
            if key not in kwargs:
                raw_key = cls._to_config(key)
                raise ValueError("Missing required config key `{}'"
                                 .format(raw_key))

        kwargs.update(extra_kwargs)
        return cls(**kwargs)


class ConfigDictNoMangleMixin(object):
    """
    A mixin which does not mangle config keys by converting `-' in
    config keys to `_' in field names (and vice versa) as
    ConfigDictMixin does by default.
    """

    @staticmethod
    def _to_field(config_key):
        """Convert a config key to a field name"""
        return config_key

    @staticmethod
    def _to_config(field_name):
        """Convert a field name to a config key"""
        return field_name

# TODO: remove
class Record(object):
    """
    A struct in Python, basically.
    Constructor sets fields according to the fields in __slots__.
    """

    def __init__(self, **kwargs):
        for arg, val in kwargs.items():
            if arg in self.__slots__:
                setattr(self, arg, val)
            else:
                raise TypeError('invalid argument to {}: {}'
                                .format(type(self), arg))

    def __repr__(self):
        props = ', '.join('{}={}'.format(prop, str(getattr(self, prop)))
                          for prop in self.__slots__ if hasattr(self, prop))
        return '<{} {}>'.format(type(self).__name__, props)
