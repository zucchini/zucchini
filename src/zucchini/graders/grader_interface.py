from abc import ABC, abstractmethod
from fractions import Fraction
from pathlib import Path
from typing import Generic, TypeVar
from typing_extensions import deprecated
from pydantic import BaseModel

from zucchini.grades import PartGrade
from zucchini.submission import Submission2
from zucchini.utils import ShlexCommand

class Part(BaseModel, ABC):
    """
    Represents a 'part' of grading which has its own weight and its own
    score: one prompt question, one unit test, etc.
    """

    weight: Fraction
    """Weight of part"""

    partial_credit: bool = True
    """Whether partial credit should be acceptable"""

    @abstractmethod
    def description(self) -> str:
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

    def list_prerequisites(self) -> list[str]:
        """
        This function should return a list of Ubuntu 16.04 packages
        required to run this grader.
        """
        return []

    def list_extra_setup_commands(self) -> list[ShlexCommand]:
        """
        This function should return a list of extra one-time commands to
        run at Docker image creation time. This is Ubuntu.
        """
        return []

    def is_interactive(self) -> bool:
        """
        Return True if and only if this grader will produce command-line
        prompts.
        """
        return False

    def needs_display(self) -> bool:
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
    def grade(self, submission: Submission2, path: Path, parts: list[P]) -> list[PartGrade]:
        """
        Grades a submission.

        Parameters
        ----------
        submission : Submission
            The submission object to grade.
        path : Path
            The path for the root submission directory.
            This is also the current directory, where commands are executed from.
        parts : list[P]
            A list of parts (from the config file).

            This will be the same type defined in `cls.Part()`
            and in the type argument for this type.

        Returns
        -------
        list[PartGrade]
            The grades for each individual part.
            There must be one for each part specified in the `parts` argument.
        """
        pass
