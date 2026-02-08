import enum
import re
from fractions import Fraction
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator

from zucchini.submission import Submission

from . import PenalizerInterface, InvalidPenalizerConfigError

"""Penalize a late submission."""


class LatePenaltyType(enum.Enum):
    PERCENT = '%'
    POINTS = 'pts'
    MAX_POINTS = 'max_pts'

UNITS_REGEX = re.compile(r'^(?P<mag>[0-9/]+)\s*(?P<unit>[a-z_-]*)$')
_UnitInput = str | int | float | Fraction

def _split_units(amount_str: _UnitInput) -> tuple[Fraction, str | None]:
    if isinstance(amount_str, int | float | Fraction):
        return Fraction(amount_str), None
    
    match = UNITS_REGEX.match(amount_str.lower())

    if match is None:
        raise InvalidPenalizerConfigError(f"unknown units format {amount_str!r}")

    return Fraction(match.group('mag')), match.group('unit') or None

def _parse_secs(time_str: _UnitInput):
    mag, unit = _split_units(time_str)
    unit = unit or "s"

    units = {'s': 1, 'm': 60, 'h': 60*60, 'd': 24*60*60}
    if unit not in units:
        raise InvalidPenalizerConfigError(f"unknown time unit {unit!r}. try one of {', '.join(units)}.")
    
    return mag * units[unit]

def _parse_penalty(penalty_str: _UnitInput):
    mag, unit = _split_units(penalty_str)

    if unit in ('pt', 'pts'):
        return (mag / 100, LatePenaltyType.POINTS)
    elif unit in ('maxpts', 'max-pts', 'max_pts', 'maxpt', 'max-pt', 'max_pt'):
        return (mag / 100, LatePenaltyType.MAX_POINTS)
    elif unit is None:
        return (mag, LatePenaltyType.PERCENT)
    else:
        raise InvalidPenalizerConfigError(f"unknown penalty unit {unit!r}. try a fraction optionally followed by 'pts' or 'max-pts'.")

class LatePenalty(BaseModel):
    after: Annotated[Fraction, BeforeValidator(_parse_secs)]
    penalty: Annotated[tuple[Fraction, LatePenaltyType], BeforeValidator(_parse_penalty)]

    def is_late(self, submission: Submission):
        return submission.seconds_late is not None \
               and submission.seconds_late > self.after

    def adjust_grade(self, grade: Fraction):
        penalty, penalty_type = self.penalty
        match penalty_type:
            case LatePenaltyType.PERCENT:
                return grade * (1 - penalty)
            case LatePenaltyType.POINTS:
                return max(Fraction(0), grade - penalty)
            case LatePenaltyType.MAX_POINTS:
                return min(grade, penalty)
            case ty:
                raise ValueError(f"unknown penalty type {ty!r}. code bug?")

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

    kind: Literal["LatePenalizer"]
    penalties: list[LatePenalty]

    def adjust_grade(self, submission: Submission, grade: Fraction):
        for penalty in self.penalties:
            if penalty.is_late(submission):
                grade = penalty.adjust_grade(grade)

        return grade
