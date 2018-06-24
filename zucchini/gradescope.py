"""
Utilities for gradescope autograding.
"""

import json

from .utils import datetime_from_string


class GradescopeMetadata(object):
    """
    Parse the metadata as described in:
    https://gradescope-autograders.readthedocs.io/en/latest/submission_metadata/
    """

    _ATTRS = {
        'id': int,
        'created_at': datetime_from_string,
        'assignment_id': int,
    }

    def __init__(self, json_dict):
        for attr, type_ in self._ATTRS.items():
            setattr(self, attr, type_(json_dict[attr]))

    @classmethod
    def from_json_path(cls, json_path):
        with open(json_path, 'r') as json_fp:
            return cls(json.load(json_fp))
