import datetime as dt
import enum
import re
from fractions import Fraction
from typing import Annotated, Literal
from typing_extensions import override

from pydantic import BeforeValidator

from zucchini.utils import KebabModel

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

def _parse_timedelta(time_str: _UnitInput):
    # If failure to split, we just let data pass
    # to allow for other timedelta formats.
    try:
        mag, unit = _split_units(time_str)
    except InvalidPenalizerConfigError:
        return time_str
    
    unit = unit or "s"
    UNITS = {
        's': dt.timedelta(seconds=1),
        'm': dt.timedelta(minutes=1),
        'h': dt.timedelta(hours=1),
        'd': dt.timedelta(days=1)
    }
    if unit not in UNITS:
        raise InvalidPenalizerConfigError(f"unknown time unit {unit!r}. try one of {', '.join(UNITS)}.")
    
    return mag.numerator * UNITS[unit] / mag.denominator

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

class LatePenalty(KebabModel):
    """
    A single penalty rule. 
    
    This applies a specified penalty only when the specified amount of time has passed.
    """

    after: Annotated[dt.timedelta, BeforeValidator(_parse_timedelta)]
    penalty: Annotated[tuple[Fraction, LatePenaltyType], BeforeValidator(_parse_penalty)]

    def is_late(self, duration_late: dt.timedelta | None):
        """Whether the submission is late under this penalty."""
        return duration_late is not None and duration_late > self.after

    def adjust_grade(self, grade: Fraction):
        """Adjust the grade as though the submission is late."""
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
    
    apply_first: bool = False
    """
    Whether to apply only the earliest applicable penalty.

    If True, this only applies the first penalty (chronologically) which is marked late.
    If False, this applies all penalties marked late.

    This field is particularly useful when thinking about penalties in terms of intervals.
    If penalties are ordered chronologically, 
    then a given penalty is applied if the submission time is between the current and next penalty.
    """

    @override
    def adjust_grade(self, grade: Fraction, submission, metadata):
        # Determine how late submission was:
        duration_late = None
        if submission.submit_date is not None and metadata.due_date is not None:
            duration_late = submission.submit_date - metadata.due_date
            
        # Apply penalties accordingly:
        penalties = sorted(self.penalties, key=lambda p: p.after)
        for penalty in penalties:
            if penalty.is_late(duration_late):
                grade = penalty.adjust_grade(grade)
                # First penalty applied, don't apply any more penalties
                if self.apply_first:
                    break

        return grade
