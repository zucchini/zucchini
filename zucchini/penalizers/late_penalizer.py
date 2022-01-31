import re
from fractions import Fraction

from . import PenalizerInterface, InvalidPenalizerConfigError
from ..utils import ConfigDictMixin

"""Penalize a late submission."""


class LatePenaltyType:
    PERCENT = '%'
    POINTS = 'pts'
    MAX_POINTS = 'max_pts'


class LatePenalty(ConfigDictMixin):
    UNITS_REGEX = re.compile(r'^(?P<mag>[0-9/]+)\s*(?P<unit>[a-z_-]*)$')

    def __init__(self, after, penalty):
        self.after = self.time_to_seconds(after)
        self.penalty, penalty_unit = self.split_units(penalty)

        if penalty_unit in ('pt', 'pts'):
            self.penalty /= 100
            self.penalty_type = LatePenaltyType.POINTS
        elif penalty_unit in ('maxpts', 'max-pts', 'max_pts',
                              'maxpt', 'max-pt', 'max_pt'):
            self.penalty /= 100
            self.penalty_type = LatePenaltyType.MAX_POINTS
        elif penalty_unit is None:
            self.penalty_type = LatePenaltyType.PERCENT
        else:
            raise InvalidPenalizerConfigError("unknown penalty unit `{}'. try "
                                              "a fraction optionally followed "
                                              "by `pts' or `max-pts'."
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
        if self.penalty_type == LatePenaltyType.PERCENT:
            return grade * (1 - self.penalty)
        elif self.penalty_type == LatePenaltyType.POINTS:
            return max(0, grade - self.penalty)
        elif self.penalty_type == LatePenaltyType.MAX_POINTS:
            return min(grade, self.penalty)
        else:
            raise ValueError("unknown penalty type `{}'. code bug?"
                             .format(self.penalty_type))


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

    The penalty unit (pts above) can be any of the following, where N is the
    number provided (e.g., N pts):

     * pt, pts: Subtract N/100, a fixed number of points, from the student's
                grade. Do not allow their grade to go below 0.

     * maxpts, max_pts, maxpt, max_pt: Set the maximum grade a student can
                                       achieve to N/100.

     * (none): Multiply the student's grade by (1-N). Here, N is expected to be
               a fraction already, e.g., 1/4.
    """

    def __init__(self, penalties):
        self.penalties = [LatePenalty.from_config_dict(p) for p in penalties]

    def adjust_grade(self, submission, grade):
        for penalty in self.penalties:
            if penalty.is_late(submission):
                grade = penalty.adjust_grade(grade)

        return grade
