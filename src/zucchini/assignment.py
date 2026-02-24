import dataclasses
import datetime as dt
from fractions import Fraction
from pathlib import Path
import tempfile
from typing import Annotated

from pydantic import BeforeValidator, Field, ValidationInfo

from zucchini.exceptions import BrokenSubmissionError, BrokenAutograderError, ZucchiniError
from zucchini.graders import SupportedGrader
from zucchini.graders.grader_interface import GraderInterface, Part
from zucchini.penalizers.late_penalizer import LatePenalizer
from zucchini.submission import Submission
from zucchini.utils import KebabModel, OptionalList, copy_globs

from .grades import AssignmentGrade, BoundPartGrade, ComponentGrade, PenaltyDeduction

def _div_or_zero(a: Fraction, b: int | Fraction):
    """
    Divides a by b, returning 0 if a division by zero error would occur.
    """
    if b == 0: return Fraction(0)
    return a / b

@dataclasses.dataclass(slots=True)
class AssignmentMetadata:
    total_points: Fraction = Fraction(100)
    """Total points the autograded portion of the assignment is worth."""

    due_date: dt.datetime | None = None
    """Date assignment is due."""

class Penalizer(KebabModel):
    """
    A penalizer config definition, which can use any defined `PenalizerInterface`.
    """

    name: str
    """Name of penalizer (displayed on Gradescope)"""

    # If we add more backends, switch this to:
    #     Annotated[SupportedPenalizer, Field(discriminator="kind")]
    backend: LatePenalizer
    """The backend to use"""

def _select_part(n, info: ValidationInfo):
    # Get backend:
    backend = info.data.get("backend")
    if not isinstance(backend, GraderInterface):
        raise ValueError("Could not resolve part due to misconfigured backend")

    return backend.create_part(n)

class AssignmentComponent(KebabModel):
    """
    A component which is graded with the same backend and files.
    """

    name: str
    """Name of component"""

    weight: Fraction
    """Weight of component"""

    backend: Annotated[SupportedGrader, Field(discriminator="kind")]
    """The backend to use"""
    
    files: OptionalList[str]
    """
    Paths (globs) copied from the submission folder.
    This should hold all files which are submitted from the user.
    """

    grading_files: OptionalList[str]
    """
    Paths (globs) copied from the grading folder.
    This should hold all files which are needed for grading.
    """

    parts: OptionalList[Annotated[Part, BeforeValidator(_select_part)]]

    def total_part_weight(self) -> Fraction:
        """Total weight defined by the parts of this component."""
        return sum((p.weight for p in self.parts), start=Fraction(0))

    def grade(self, submission: Submission, total_component_weight: Fraction, test_dir: Path) -> ComponentGrade:
        with tempfile.TemporaryDirectory(prefix="zcomponent-") as grading_dir:
            grading_dir = Path(grading_dir)
            parts_: list = self.parts
            norm_weight = _div_or_zero(self.weight, total_component_weight)

            try:
                try:
                    # Copy all submission files over
                    copy_globs(self.files, submission.submission_dir, grading_dir)
                except FileNotFoundError as e:
                    # This is user's fault
                    raise BrokenSubmissionError(str(e)) from e
            
                # Copy all grading files over
                copy_globs(self.grading_files, test_dir, grading_dir)

                # Perform grading:
                grades = self.backend.grade(submission, grading_dir, parts_)

            except ZucchiniError as e:
                return ComponentGrade(norm_weight=norm_weight, description=self.name, error=e)
            except Exception as e:
                # If something breaks, we assume autograder broke it:
                ze = BrokenAutograderError(str(e))
                return ComponentGrade(norm_weight=norm_weight, description=self.name, error=ze)
            
            total_part_weight = self.total_part_weight()
            parts = [
                BoundPartGrade(
                    inner=g,
                    description=p.description(),
                    norm_weight=_div_or_zero(p.weight, total_part_weight)
                )
                for (p, g) in zip(self.parts, grades)
            ]
            return ComponentGrade(norm_weight=norm_weight, description=self.name, parts=parts)


class AssignmentConfig(KebabModel):
    """
    A full assignment, which can be graded.
    """

    name: str
    """Name of assignment"""

    author: str | None = None
    """Author of assignment"""

    penalties: OptionalList[Penalizer]
    """Any penalizers to impose on the assignment (e.g., late penalty)"""

    components: OptionalList[AssignmentComponent]
    """
    Individual components which use the same backend and file configuration.
    """

    def total_component_weight(self) -> Fraction:
        """Total weight defined by the components of this assignment."""
        return sum((c.weight for c in self.components), start=Fraction(0))


@dataclasses.dataclass
class Assignment:
    config: AssignmentConfig
    """
    The Zucchini configuration for the assignment,
    which specifies how it should be autograded.
    """

    grading_dir: Path
    """
    Directory where grading files are located.
    """

    metadata: AssignmentMetadata
    """
    The metadata for the assignment,
    which may be used to inform grading decisions.
    """
    
    def grade(self, submission: Submission):
        component_grades = [c.grade(submission, self.config.total_component_weight(), self.grading_dir) for c in self.config.components]
        penalties: list[PenaltyDeduction] = []
        
        raw_grade = sum((cg.points_received() for cg in component_grades), start=Fraction(0))
        adjusted_grade = raw_grade
        for p in self.config.penalties:
            new_adjusted_grade = p.backend.adjust_grade(adjusted_grade, submission, self.metadata)

            penalties.append(PenaltyDeduction(
                name=p.name,
                points_deducted=(adjusted_grade - new_adjusted_grade)
            ))
            adjusted_grade = new_adjusted_grade
        

        return AssignmentGrade(
            name=self.config.name,
            raw_score=raw_grade,
            final_score=adjusted_grade,
            max_points=self.metadata.total_points,
            components=component_grades,
            penalties=penalties
        )
