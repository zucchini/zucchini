from abc import ABC, abstractmethod
from fractions import Fraction

from zucchini.utils import KebabModel

from zucchini.model import AssignmentMetadata
from zucchini.submission import Submission2

class PenalizerInterface(KebabModel, ABC):
    """Penalize a student outside component grades. Example: Late penalties"""
    
    @abstractmethod
    def adjust_grade(self, grade: Fraction, submission: Submission2, metadata: AssignmentMetadata) -> Fraction:
        """
        This function should take in a Submission object and a Fraction
        holding the calculated grade, returning the new grade.
        """
        pass
