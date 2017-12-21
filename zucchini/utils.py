import errno
import os
import re

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
