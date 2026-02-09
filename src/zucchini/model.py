
from abc import ABC, abstractmethod
import dataclasses
import datetime
from fractions import Fraction
from pathlib import Path
import tempfile
from typing import Annotated
from pydantic import BaseModel, BeforeValidator, Field, ValidationInfo

from zucchini.exceptions import BrokenSubmissionError
from zucchini.grades import BoundPartGrade, ComponentGrade2
from zucchini.submission import Submission2
from zucchini.utils import copy_globs

from .graders import SupportedGrader
from .graders.grader_interface import GraderInterface, Part
from .penalizers.late_penalizer import LatePenalizer

def _div_or_zero(a: Fraction, b: int | Fraction):
    """
    Divides a by b, returning 0 if a division by zero error would occur.
    """
    if b == 0: return Fraction(0)
    return a / b

@dataclasses.dataclass(slots=True)
class AssignmentMetadata:
    total_points: Fraction
    """Total points the autograded portion of the assignment is worth."""

    tester_dir: Path
    """Directory where test/grading files are located."""

    due_date: datetime.datetime | None = None
    """Date assignment is due."""

class IntoMetadata(ABC):
    """Indicates this type can be converted into `AssignmentMetadata`."""
    @abstractmethod
    def as_metadata(self, tester_dir: Path) -> AssignmentMetadata:
        """Converts the type into metadata."""
        pass

class Penalizer(BaseModel):
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

    return backend.Part()(**n)

class AssignmentComponent(BaseModel):
    """
    A component which is graded with the same backend and files.
    """

    name: str
    """Name of component"""

    weight: Fraction
    """Weight of component"""

    backend: Annotated[SupportedGrader, Field(discriminator="kind")]
    """The backend to use"""
    
    files: list[str]
    """
    Paths (globs) copied from the submission folder.
    This should hold all files which are submitted from the user.
    """

    grading_files: list[str]
    """
    Paths (globs) copied from the grading folder.
    This should hold all files which are needed for grading.
    """

    parts: list[Annotated[Part, BeforeValidator(_select_part)]]

    def total_part_weight(self) -> Fraction:
        """Total weight defined by the parts of this component."""
        return sum((p.weight for p in self.parts), start=Fraction(0))

    def grade(self, submission: Submission2, total_component_weight: Fraction, asg_metadata: AssignmentMetadata) -> ComponentGrade2:
        with tempfile.TemporaryDirectory(prefix="zcomponent-") as grading_dir:
            grading_dir = Path(grading_dir)
            parts_: list = self.parts
            
            # Copy all submission files over
            copy_globs(self.files, submission.submission_dir, grading_dir)
            # Copy all grading files over
            copy_globs(self.grading_files, asg_metadata.tester_dir, grading_dir)

            # Perform grading:
            norm_weight = _div_or_zero(self.weight, total_component_weight)
            try:
                grades = self.backend.grade(submission, grading_dir, parts_)
            except BrokenSubmissionError as e:
                return ComponentGrade2(norm_weight=norm_weight, error=e)
            
            total_part_weight = self.total_part_weight()
            parts = [
                BoundPartGrade(
                    inner=g,
                    description=p.description(),
                    norm_weight=_div_or_zero(p.weight, total_part_weight)
                )
                for (p, g) in zip(self.parts, grades)
            ]
            return ComponentGrade2(norm_weight=norm_weight, parts=parts)


class AssignmentConfig(BaseModel):
    """
    A full assignment, which can be graded.
    """

    name: str
    """Name of assignment"""

    author: str | None = None
    """Author of assignment"""

    penalties: list[Penalizer]
    """Any penalizers to impose on the assignment (e.g., late penalty)"""

    components: list[AssignmentComponent]
    """
    Individual components which use the same backend and file configuration.
    """

    def total_component_weight(self) -> Fraction:
        """Total weight defined by the components of this assignment."""
        return sum((c.weight for c in self.components), start=Fraction(0))