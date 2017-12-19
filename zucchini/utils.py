import errno
import os
import re

import click


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class EmailParamType(click.ParamType):
    name = 'email'
    regex = '^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*' \
            '(\.[a-z]{2,4})$'

    def convert(self, value, param, ctx):
        if re.match(EmailParamType.regex, value) is None:
            self.fail('%s is not a valid email address' % value, param, ctx)

        return value
