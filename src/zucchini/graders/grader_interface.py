from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar
from typing_extensions import deprecated
from pydantic import BaseModel

from zucchini.grades import PartGrade
from zucchini.submission import Submission

class Part(BaseModel, ABC):
    """
    Represents a 'part' of grading which has its own weight and its own
    score: one prompt question, one unit test, etc.
    """

    weight: int
    """Weight of part"""
    # TODO: consider fractionalizing this?

    partial_credit: bool = True
    """Whether partial credit should be acceptable"""

    @abstractmethod
    def description(self):
        """
        Return a human-friendly description for this part. Used in grade
        breakdowns and logs.
        """
        pass

P = TypeVar("P", bound=Part)
class GraderInterface(BaseModel, ABC, Generic[P]):
    @classmethod
    @abstractmethod
    def Part(cls) -> type[P]:
        """
        The part type of the grader.

        You should return the class directly (e.g., `return Part`).
        """
        pass

    def list_prerequisites(self):
        """
        This function should return a list of Ubuntu 16.04 packages
        required to run this grader.
        """
        return []

    def list_extra_setup_commands(self):
        """
        This function should return a list of extra one-time commands to
        run at Docker image creation time. This is Ubuntu.
        """
        return []

    def is_interactive(self):
        """
        Return True if and only if this grader will produce command-line
        prompts.
        """
        return False

    def needs_display(self):
        """
        Return True if and only if this grader expects a graphical
        environment, like $DISPLAY on GNU/Linux. Does not necessarily
        imply is_interactive() is True since some graders are
        noninteractive but still connect to a display server, like
        CircuitSim graders (since CircuitSim needs JavaFX).
        """
        return False

    @deprecated("should be able to just pass in parts directly")
    def part_from_config_dict(self, config_dict) -> P: 
        """
        Convert and validate a dictionary parsed from the `parts'
        section of a component configuration to a Part instance.
        """
        return self.Part()(**config_dict)

    @abstractmethod
    def grade(self,
              submission: Submission,
              path: Path,
              parts: list[P]) -> list[PartGrade]:
        """
        This function should take in a Submission object and a path,
        where the path can be assumed to be the root of the submission
        directory (it will be a directory where the grading manager has
        copied the required files for this grader); then complete the
        grading on it, and then return a list of kasjdfkasjdfkj
        instances containing the result for each subcomponent.
        """
        pass
