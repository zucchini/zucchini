import re
from fractions import Fraction
import requests
import json
from ..utils import ConfigDictMixin


from . import PenalizerInterface, InvalidPenalizerConfigError

"""Penalize a submission after being checked off."""


class AttendanceLoader(ConfigDictMixin):

    def __init__(self, google_api_url, google_api_key, sheet_id, name_range):
        self.google_api_url = google_api_url
        self.google_api_key = google_api_key
        self.sheet_id = sheet_id
        self.name_range = name_range

    def load_students(self):
        students = []
        spreadsheet = requests.get(self.google_api_url + "%s?key=%s" % (self.sheet_id, self.google_api_key)).json()

        for sheet in spreadsheet["sheets"]:
            name_range = sheet["properties"]["title"] + "!" + self.name_range
            student_values = requests.get(
                self.google_api_url + "%s/values/%s?key=%s" % (self.sheet_id, name_range, self.google_api_key)).json()
            if "values" in student_values:
                for student in student_values["values"]:
                    students.append(student[0])
        return students


class CheckoffPenalizer(PenalizerInterface):
    UNITS_REGEX = re.compile(r'^(?P<mag>[0-9/]+)\s*(?P<unit>[a-z]*)$')
    """
    Penalize students for submitting after being checked off on the attendance sheet.

    Configure it like this in the assignment config file. In this
    example, after 8 hours late you get 75 points off your grade (a 85
    would go to a 10).

    penalties:
    - name: CHECKOFF
      backend: CheckoffPenalizer
      backend-options:
        penalty: 100pts
        config:
            google-api-url: https://sheets.googleapis.com/v4/spreadsheets/
            google-api-key: dfbus9fd8byiuydfis098s7d0875ga
            sheet-id: asdfatfb7d65fga8967s5d87a4sd
            name-range: 'B2:B'

    """

    def __init__(self, penalty, config):
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

        self.loader = AttendanceLoader.from_config_dict(config)

    def adjust_grade(self, submission, grade):
        students = self.loader.load_students()
        if submission.student_name in students:
            if self.penalty_points:
                grade = max(0, grade - self.penalty)
                print(grade)
                return grade
            else:
                grade = grade * (1 - self.penalty)
                print(grade)
                return grade
        return grade


    @classmethod
    def split_units(cls, amount_str):
        if isinstance(amount_str, (int, float)):
            return Fraction(amount_str), None

        match = cls.UNITS_REGEX.match(amount_str.lower())

        if match is None:
            raise InvalidPenalizerConfigError("unknown units format `{}'"
                                              .format())

        return Fraction(match.group('mag')), match.group('unit') or None


