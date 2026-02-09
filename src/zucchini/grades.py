from fractions import Fraction
from typing import Annotated

from pydantic import BaseModel, PlainSerializer, PlainValidator

from zucchini.exceptions import BrokenSubmissionError

"""Store grades for components and parts."""

class PartGrade(BaseModel):
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

class BoundPartGrade(BaseModel):
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
        return self.inner.score == 1
    
    def points_received(self) -> Fraction:
        """The points received for this part, using normalized weight."""
        return self.inner.score * self.norm_weight

class ComponentGrade(BaseModel):
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

    error: Annotated[
        BrokenSubmissionError,
        PlainValidator(lambda s: BrokenSubmissionError(s["error"], s["verbose"])),
        PlainSerializer(lambda e: { "error": str(e), "verbose": e.verbose })
    ] | None = None
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
    
class PenaltyDeduction(BaseModel):
    name: str
    """Name of the deduction."""

    points_deducted: Fraction
    """Amount of points deducted due to this penalty."""

class AssignmentGrade(BaseModel):
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

    components: list[ComponentGrade]
    """Grades from components."""

    penalties: list[PenaltyDeduction]
    """Any penalty deductions."""

    def final_grade(self) -> Fraction:
        """Final grade, scaled to the number of points."""
        return self.final_score * self.max_points
