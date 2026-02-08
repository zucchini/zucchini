from fractions import Fraction
from typing import Annotated, Literal

from pydantic import Field

from ..utils import ShlexCommand, run_command
from ..grades import PartGrade
from . import GraderInterface, Part

"""
Grade a homework by execuing a bunch of commands
"""


class Command(Part):
    """A command to execute"""

    summary: str
    """
    A text description of the command (displayed on Gradescope)
    """

    command: ShlexCommand
    """
    The command to execute.
    """

    def description(self):
        return self.summary

    def grade(self, path, timeout):
        cmd_result = run_command(self.command, cwd=path, timeout=timeout)
        log = cmd_result.stdout

        if cmd_result.returncode:
            score = Fraction(0)
            log += f'\n\ngrader exited with exit code {cmd_result.returncode} != 0'
        else:
            score = Fraction(1)

        return PartGrade(score=score, log=log)


class MultiCommandGrader(GraderInterface):
    """
    Run a bunch of commands, testing the exit code of each.
    """

    kind: Literal["MultiCommandGrader"]
    
    timeout: float = 30
    """Timeout of autograder."""

    extra_setup_commands: Annotated[list[ShlexCommand], Field(default_factory=list)]

    def list_extra_setup_commands(self):
        return self.extra_setup_commands

    @classmethod
    def Part(cls):
        return Command

    def grade(self, submission, path, parts):
        return [part.grade(path, self.timeout) for part in parts]
