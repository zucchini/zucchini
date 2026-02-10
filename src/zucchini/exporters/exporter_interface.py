from abc import ABC, abstractmethod
import functools
from typing import Callable, TextIO, TypeVar

from zucchini.grades import AssignmentGrade


class ExporterInterface(ABC):
    @abstractmethod
    def export(self, grade: AssignmentGrade, output: TextIO):
        """
        Take in a grade format and writes it to the output field.
        """
        pass

E = TypeVar("E", bound=ExporterInterface)
def _export_str(c: Callable[[E, AssignmentGrade], str]) -> Callable[[E, AssignmentGrade, TextIO], None]:
    """
    Decorator which takes a function that produces a string from the specified grade
    and converts it into the export format required by `ExporterInterface`.
    """

    @functools.wraps(c)
    def export(self: E, grade: AssignmentGrade, output: TextIO):
        output.write(c(self, grade))
    
    return export
