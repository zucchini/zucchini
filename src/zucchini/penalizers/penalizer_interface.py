from abc import ABC, abstractmethod
from fractions import Fraction

from pydantic import BaseModel

from zucchini.submission import Submission

class PenalizerInterface(BaseModel, ABC):
    """Penalize a student outside component grades. Example: Late penalties"""
    
    @abstractmethod
    def adjust_grade(self, submission: Submission, grade: Fraction) -> Fraction:
        """
        This function should take in a Submission object and a Fraction
        holding the calculated grade, returning the new grade.
        """
        pass
