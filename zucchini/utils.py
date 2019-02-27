import sys
import errno
import os
import re
import inspect
import glob
import shutil
import threading
from collections import namedtuple

import arrow
import click

if sys.version_info[0] < 3:
    # subprocess32, the python 3 subprocess module backported to python
    # 2, does not support non-POSIX platforms (aka Windows). So if
    # you're on Windows, you need to use python 3, since it has a more
    # up-to-date subprocess module in the standard library
    if os.name != 'posix':
        raise NotImplementedError('You need to use Python 3 on non-POSIX '
                                  'platforms')

    # Python 2 imports
    import Queue as queue  # noqa
    import subprocess32 as subprocess
    from urlparse import urlparse
else:
    # Python 3 imports
    import queue  # noqa
    import subprocess
    from urllib.parse import urlparse


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def recursive_get_using_string(collection, key):
    """
    Given a collection and a key in the format of x.y.z.a, return collection
    [x][y][z][a].
    """

    if "." not in key:
        if key.isdigit():
            key = int(key)

        return collection[key]

    left, right = key.split('.', 1)
    return recursive_get_using_string(
            recursive_get_using_string(collection, left),
            right)


def run_thread(func, args, result_queue):
    """
    Run a thread which runs func(args), putting each yielded result in
    queue. Return the thread.
    """

    def thread():
        try:
            for result in func(*args):
                result_queue.put(result)
        except Exception as err:
            result_queue.put(err)

    thread = threading.Thread(target=thread)
    thread.start()
    return thread


# Patch around old versions of subprocess
PIPE = subprocess.PIPE
STDOUT = subprocess.STDOUT
TimeoutExpired = subprocess.TimeoutExpired
CompletedProcess = namedtuple('CompletedProcess', ('args', 'returncode',
                                                   'stdout', 'stderr'))


def run_process(*popenargs, **kwargs):
    """
    A straight copy-paste of subprocess.run() from the CPython source to
    support Python versions earlier than 3.5.
    """

    # Can't put these directly in function signature because PEP-3102 is
    # not a thing in Python 2
    input = kwargs.pop('input', None)
    timeout = kwargs.pop('timeout', None)
    check = kwargs.pop('check', False)

    if input is not None:
        if 'stdin' in kwargs:
            raise ValueError('stdin and input arguments may not both be used.')
        kwargs['stdin'] = subprocess.PIPE

    with subprocess.Popen(*popenargs, **kwargs) as process:
        try:
            stdout, stderr = process.communicate(input, timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            raise subprocess.TimeoutExpired(process.args, timeout,
                                            output=stdout, stderr=stderr)
        except: # noqa
            process.kill()
            process.wait()
            raise
        retcode = process.poll()
        if check and retcode:
            raise subprocess.CalledProcessError(retcode, process.args,
                                                output=stdout, stderr=stderr)

    return CompletedProcess(process.args, retcode, stdout, stderr)


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


# Support FileNotFoundError, which does not exist in Python 2
try:
    FileNotFoundError = FileNotFoundError
except NameError:
    class FileNotFoundError(Exception):
        pass


def copy_globs(globs, src_dir, dest_dir):
    """
    Copy files matched by `globs' (a list of glob strings) from src_dir
    to dest_dir, maintaining directories if possible.
    """

    files_to_copy = []

    # Do a first pass to check for missing files. This way, we don't
    # copy a bunch of files only to blow up when we can't find a
    # later file.
    for file_glob in globs:
        absolute_glob = os.path.join(src_dir, file_glob)
        matches = glob.iglob(absolute_glob)

        if not matches:
            raise FileNotFoundError("missing file `{}'".format(file_glob))

        files_to_copy += matches

    for file_to_copy in files_to_copy:
        relative_path = os.path.relpath(file_to_copy, start=src_dir)
        dirname = os.path.dirname(relative_path)

        dest = os.path.join(dest_dir, relative_path)
        if os.path.isdir(file_to_copy):
            shutil.copytree(file_to_copy, dest)
        else:
            mkdir_p(os.path.join(dest_dir, dirname))
            shutil.copy(file_to_copy, dest)


# Same as the Canvas date format
_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


def datetime_from_string(date_str):
    """
    Convert a human-readable date/time string (in the format used by
    Canvas and in submission metadata files) to a datetime instance.
    """

    return arrow.get(date_str).to('utc').datetime


def datetime_to_string(datetime_obj):
    """Convert a datetime UTC instance to a human-readable date/time string."""

    return datetime_obj.strftime(_DATETIME_FORMAT)


def current_iso8601():
    return arrow.now().replace(microsecond=0).isoformat()


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

        arg_spec = inspect.getargspec(cls.__init__)
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


class CanvasURLType(click.ParamType):
    name = 'http(s) url'

    def convert(self, value, param, ctx):
        parsed = urlparse(value)
        # Be picky and demand https://... and no querystrings or
        # fragments or other weird stuff
        valid_https_url = parsed.scheme == 'https' \
            and '.' in parsed.netloc and parsed.path in ('/', '') \
            and not parsed.params and not parsed.query \
            and not parsed.fragment and not parsed.username \
            and not parsed.password

        if not valid_https_url:
            self.fail("`{}' is not a valid Canvas URL. I want something "
                      "like https://gatech.instructure.com/"
                      .format(value), param, ctx)

        # Strip trailing slash
        if value.endswith('/'):
            value = value[:-1]

        return value


CANVAS_URL = CanvasURLType()


class AwsAccessKeyIdType(click.ParamType):
    name = 'AWS Access Key ID'

    def convert(self, value, param, ctx):
        # TODO: actual error handling for AWS Access Key ID
        return value.strip()


AWS_ACCESS_KEY_ID = AwsAccessKeyIdType()


class AwsSecretAccessKeyType(click.ParamType):
    name = 'AWS Secret Access Key'

    def convert(self, value, param, ctx):
        # TODO: actual error handling for AWS Secret Access Key
        return value.strip()


AWS_SECRET_ACCESS_KEY = AwsSecretAccessKeyType()


class AwsBucketNameType(click.ParamType):
    name = 'AWS Bucket Name'

    def convert(self, value, param, ctx):
        # TODO: actual error handling for AWS Bucket Name
        return value.strip()


AWS_BUCKET_NAME = AwsBucketNameType()


class CanvasTokenType(click.ParamType):
    name = 'canvas token'

    def convert(self, value, param, ctx):
        value = value.strip()

        if not re.match(r'^[A-Za-z0-9]{64}$', value):
            self.fail("`{}' is not a valid Canvas token. Should be 64 "
                      "alphanumeric characters.".format(value), param, ctx)

        return value


CANVAS_TOKEN = CanvasTokenType()


class EmailParamType(click.ParamType):
    name = 'email'
    regex = r'^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*' \
            r'(\.[a-z]{2,4})$'

    def convert(self, value, param, ctx):
        if re.match(EmailParamType.regex, value) is None:
            self.fail('%s is not a valid email address' % value, param, ctx)

        return value
