import re
from fractions import Fraction

from . import PenalizerInterface, InvalidPenalizerConfigError
from ..utils import ConfigDictMixin

"""Penalize a late submission."""


class LatePenalty(ConfigDictMixin):
    UNITS_REGEX = re.compile(r'^(?P<mag>[0-9/]+)\s*(?P<unit>[a-z]*)$')

    def __init__(self, after, penalty):
        self.after = self.time_to_seconds(after)
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

    @classmethod
    def split_units(cls, amount_str):
        if isinstance(amount_str, (int, float)):
            return Fraction(amount_str), None

        match = cls.UNITS_REGEX.match(amount_str.lower())

        if match is None:
            raise InvalidPenalizerConfigError("unknown units format `{}'"
                                              .format(amount_str))

        return Fraction(match.group('mag')), match.group('unit') or None

    @classmethod
    def time_to_seconds(cls, time_str):
        mag, unit = cls.split_units(time_str)

        unit = unit or 's'
        units = {'s': 1, 'm': 60, 'h': 60*60, 'd': 24*60*60}

        if unit not in units:
            raise InvalidPenalizerConfigError("unknown time unit `{}'. try "
                                              "one of {}"
                                              .format(unit, ', '.join(units)))
        return mag * units[unit]

    def is_late(self, submission):
        return submission.seconds_late is not None \
               and submission.seconds_late > self.after

    def adjust_grade(self, grade):
        if self.penalty_points:
            return max(0, grade - self.penalty)
        else:
            return grade * (1 - self.penalty)


class LatePenalizer(PenalizerInterface):
    """
    Penalize students for late submissions.

    Configure it like this in the assignment config file. In this
    example, after 8 hours late you get 75 points off your grade (a 85
    would go to a 10).

    penalties:
    - name: LATE
      backend: LatePenalizer
      backend-options:
        penalties:
        - after: 1h
          penalty: 25pts
        - after: 8h
          penalty: 50pts

    That is, penalties are applied in order, and they do not stop when
    there is a match. They don't necessarily have to be in increasing
    order of `after' values.
    """

    def __init__(self, penalties):
        self.penalties = [LatePenalty.from_config_dict(p) for p in penalties]

    def adjust_grade(self, submission, grade):
        for penalty in self.penalties:
            if penalty.is_late(submission):
                grade = penalty.adjust_grade(grade)

        return grade
