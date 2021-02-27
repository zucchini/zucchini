import re
from fractions import Fraction
import requests
import json


from . import PenalizerInterface, InvalidPenalizerConfigError

"""Penalize a submission after being checked off."""


class CheckoffPenalizer(PenalizerInterface):
    UNITS_REGEX = re.compile(r'^(?P<mag>[0-9/]+)\s*(?P<unit>[a-z]*)$')
    """
    Penalize students for submitting after being checked off
    on the attendance sheet.

    Configure it like this in the assignment config file. In this
    example, after 8 hours late you get 75 points off your grade (a 85
    would go to a 10).

    penalties:
    - name: CHECKOFF
      backend: CheckoffPenalizer
      backend-options:
        penalty: 100pts
        api-url: https:/.....
        api-key: djfal;ksf

    """

    def __init__(self, penalty, api_url, api_key):
        self.penalty, penalty_unit = self.split_units(penalty)
        if penalty_unit in ('pt', 'pts'):
            self.penalty /= 100
            self.penalty_points = True
        elif penalty_unit is None:
            self.penalty_points = False
        else:
            raise InvalidPenalizerConfigError("unknown penalty unit `{}'. try "
                                              "a fraction optionally followed "
                                              "by `pt'."
                                              .format(penalty_unit))

        self.api_url = api_url
        self.api_key = api_key

    def adjust_grade(self, submission, grade):
        params = {
            "student_name": submission.student_name,
            "attendance_event": submission.assignment.name
        }
        check = requests.post(url=self.api_url, data=json.dumps(params),
                              headers={"x-api-key": self.api_key})
        if check.json():
            if self.penalty_points:
                grade = max(0, grade - self.penalty)
                return grade
            else:
                grade = grade * (1 - self.penalty)
                return grade
        return grade

    @classmethod
    def split_units(cls, amount_str):
        if isinstance(amount_str, (int, float)):
            return Fraction(amount_str), None

        match = cls.UNITS_REGEX.match(amount_str.lower())

        if match is None:
            raise InvalidPenalizerConfigError("unknown units format `{}'"
                                              .format(amount_str))

        return Fraction(match.group('mag')), match.group('unit') or None
