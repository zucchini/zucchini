
from fractions import Fraction
from pathlib import Path
from typing import Annotated
from pydantic import BaseModel, BeforeValidator, Field, ValidationInfo

from .graders import SupportedGrader
from .graders.grader_interface import GraderInterface, Part
from .penalizers.late_penalizer import LatePenalizer

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
    
    files: list[Path]
    """
    Paths (globs) copied from the submission folder.
    This should hold all files which are submitted from the user.
    """

    grading_files: list[Path]
    """
    Paths (globs) copied from the grading folder.
    This should hold all files which are needed for grading.
    """

    parts: list[Annotated[Part, BeforeValidator(_select_part)]]

class Assignment(BaseModel):
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
