import errno
import os
import re
import inspect
from datetime import datetime

try:
    # Python 3
    from urllib.parse import urlparse
except ImportError:
    # Python 2
    from urlparse import urlparse

import click


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


# Same as the Canvas date format
_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%SZ'


def datetime_from_string(date_str):
    """
    Convert a human-readable date/time string (in the format used by
    Canvas and in submission metadata files) to a datetime instance.
    """

    return datetime.strptime(date_str, _DATETIME_FORMAT)


def datetime_to_string(datetime_obj):
    """Convert a datetime UTC instance to a human-readable date/time string."""

    return datetime_obj.strftime(_DATETIME_FORMAT)


class FromConfigDictMixin(object):
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
        arg_spec = inspect.getargspec(cls.__init__)
        num_optional_args = 0 if arg_spec.defaults is None \
            else min(len(arg_spec.args)-1, len(arg_spec.defaults))

        required_args = [arg for arg in arg_spec.args[1:-num_optional_args]
                         if arg not in extra_kwargs]
        optional_args = [arg for arg in arg_spec.args[-num_optional_args:]
                         if arg not in extra_kwargs]

        kwargs = {}

        for raw_key in config_dict:
            key = raw_key.replace('-', '_')

            if key not in required_args + optional_args:
                raise ValueError("Unknown config key `{}'".format(raw_key))

            kwargs[key] = config_dict[raw_key]

        for key in required_args:
            if key not in kwargs:
                raw_key = key.replace('_', '-')
                raise ValueError("Missing required config key `{}'"
                                 .format(raw_key))

        kwargs.update(extra_kwargs)
        return cls(**kwargs)


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
    regex = '^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*' \
            '(\.[a-z]{2,4})$'

    def convert(self, value, param, ctx):
        if re.match(EmailParamType.regex, value) is None:
            self.fail('%s is not a valid email address' % value, param, ctx)

        return value
