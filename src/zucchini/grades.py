import dataclasses
from fractions import Fraction

from zucchini.exceptions import BrokenSubmissionError

from .utils import ConfigDictMixin, Record

"""Store grades for components and parts."""

@dataclasses.dataclass(slots=True)
class PartGrade:
    """
    The result of grading a singular part.

    This is produced by Graders to indicate how complete a part is.
    """

    score: Fraction | int
    """The percentage correct (must be in [0, 1])."""

    deductions: list[str] | None = None
    """
    A list of strings which specify reasons points were deducted.
    This is purely descriptive and will be shown to the end-user.
    """

    log: str | None = None
    """Verbose logs after grading this part."""

@dataclasses.dataclass(slots=True)
class BoundPartGrade:
    """
    The result of grading a singular part and applying appropriate weights to it.
    """

    inner: PartGrade
    """
    Unweighted result.
    """

    description: str
    """
    Description of part (will be displayed on Gradescope)
    """

    norm_weight: Fraction
    """
    Normalized weight of part (within a component, is in [0, 1]).
    """

    def passed(self) -> bool:
        """Whether this part passed."""
        return self.inner == 1
    
    def points_received(self) -> Fraction:
        """The points received for this part, using normalized weight."""
        return self.inner.score * self.norm_weight

@dataclasses.dataclass(slots=True)
class ComponentGrade2:
    """
    The result of grading an assignment component.
    """

    norm_weight: Fraction
    """
    Normalized weight of component (within an assignment, is in [0, 1]).
    """

    description: str | None = None
    """
    Description for component.
    """

    parts: list[BoundPartGrade] | None = None
    """
    Grades of each part in the component.

    This may be none if the component produced a `BrokenSubmissionError`.
    """

    error: BrokenSubmissionError | None = None
    """
    Any submission errors which occurred during grading.

    This is `None` if no error occurred.
    """

    def passed(self) -> bool:
        """Whether this component passed."""
        return (
            self.error is not None
            and self.parts is not None
            and all(p.passed() for p in self.parts)
        )
    
    def points_received(self) -> Fraction:
        """The total number of points received for this component, using normalized weight and prior to any applied penalties."""
        if self.error or self.parts is None:
            return Fraction(0)
        return sum((p.points_received() for p in self.parts), start=Fraction(0)) * self.norm_weight
    

@dataclasses.dataclass(slots=True)
class PenaltyDeduction:
    name: str
    """Name of the deduction."""

    points_deducted: Fraction
    """Amount of points deducted due to this penalty."""

@dataclasses.dataclass(slots=True)
class AssignmentGrade2:
    """
    The result of grading the assignment.
    """

    name: str
    """
    The name of the assignment.
    """
    raw_score: Fraction
    """Normalized grade before penalties (in [0, 1])."""
    final_score: Fraction
    """Normalized grade after penalties (in [0, 1])."""

    max_points: Fraction
    """Maximum number of points."""

    components: list[ComponentGrade2]
    """Grades from components."""

    penalties: list[PenaltyDeduction]
    """Any penalty deductions."""

    def final_grade(self) -> Fraction:
        """Final grade, scaled to the number of points."""
        return self.final_score * self.max_points

class AssignmentComponentGrade(ConfigDictMixin):
    """Hold the score for an assignment component."""

    def __init__(self, part_grades=None, error=None, error_verbose=None):
        self.part_grades = part_grades
        self.error = error
        self.error_verbose = error_verbose

        if (self.part_grades is None) == (self.error is None):
            raise ValueError('need to specify either part-grades or error in '
                             'an AssignmentComponentGrade, but not both')

    def __repr__(self):
        return '<AssignmentComponentGrade part_grades={}>' \
               .format(self.part_grades)

    @classmethod
    def from_config_dict(cls, dict_):
        grade = super(AssignmentComponentGrade, cls).from_config_dict(dict_)
        if grade.part_grades:
            grade.part_grades = [PartGrade.from_config_dict(g)
                                 for g in grade.part_grades]
        return grade

    def to_config_dict(self, *args):
        dict_ = super(AssignmentComponentGrade, self).to_config_dict(*args)
        if dict_.get('part-grades', None):
            dict_['part-grades'] = [g.to_config_dict()
                                    for g in dict_['part-grades']]
        return dict_

    def is_broken(self):
        """
        Return True if and only if this submission was 'broken'; that
        is, processing it produced an unrecoverable error such as a
        missing file or noncompiling code.
        """
        return self.error is not None

    def calculate_grade(self, points, name, total_part_weight,
                        component_parts):
        """
        Using the list of ComponentPart instances provided (which
        contain the weight of components) and the part grades held in
        this instance, calculate the CalculatedComponentGrade tree for
        this grade.
        """

        grade = CalculatedComponentGrade(name=name,
                                         points_delta=Fraction(0),
                                         points_got=Fraction(0),
                                         points_possible=Fraction(0),
                                         grade=Fraction(1),
                                         error=None,
                                         error_verbose=None,
                                         parts=[])

        grade.grade = Fraction(0)

        if self.is_broken():
            grade.points_got = Fraction(0)
            grade.error = self.error
            grade.error_verbose = self.error_verbose
        else:
            for part, part_grade in zip(component_parts, self.part_grades):
                calc_part_grade = part.calculate_grade(
                    points, total_part_weight, part_grade)
                grade.parts.append(calc_part_grade)
                grade.points_got += calc_part_grade.points_got
                grade.grade += part_grade.score * Fraction(part.weight,
                                                           total_part_weight)

        grade.points_possible = points
        grade.points_delta = grade.points_got - grade.points_possible

        return grade

class CalculatedGrade(Record):
    """
    Hold the results of grading an assignment. Any numbers are a
    Fraction instance representing actual over possible.
    """
    __slots__ = ['name', 'grade', 'raw_grade', 'penalties', 'components']


class CalculatedPenalty(Record):
    """
    Hold the result of applying (or not applying) a penalty. Any numbers
    are a Fraction instance representing actual over possible.
    """
    __slots__ = ['name', 'points_delta']


class CalculatedComponentGrade(Record):
    """
    Hold the result of grading an assignment component. If error is not
    None, it is an error message string explaining why the submission is
    broken. Any numbers are a Fraction instance representing actual over
    possible.
    """
    __slots__ = ['name', 'points_delta', 'points_got', 'points_possible',
                 'grade', 'error', 'error_verbose', 'parts']


class CalculatedPartGrade(Record):
    """
    Hold the result of grading a single part (test) of an assignment
    component. Any numbers are a Fraction instance representing actual
    over possible.
    """
    __slots__ = ['name', 'points_delta', 'points_got', 'points_possible',
                 'grade', 'deductions', 'log']
