from abc import ABC, abstractmethod
from fractions import Fraction
from typing import TYPE_CHECKING

from zucchini.utils import KebabModel

if TYPE_CHECKING:
    from zucchini.assignment import AssignmentMetadata
from zucchini.submission import Submission

class PenalizerInterface(KebabModel, ABC):
    """Penalize a student outside component grades. Example: Late penalties"""
    
    @abstractmethod
    def adjust_grade(self, grade: Fraction, submission: Submission, metadata: "AssignmentMetadata") -> Fraction:
        """
        This function should take in a Submission object and a Fraction
        holding the calculated grade, returning the new grade.
        """
        pass
