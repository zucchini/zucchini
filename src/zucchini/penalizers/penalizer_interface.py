from abc import ABC, abstractmethod

from pydantic import BaseModel

class PenalizerInterface(BaseModel, ABC):
    """Penalize a student outside component grades. Example: Late penalties"""
    
    @abstractmethod
    def adjust_grade(self,
                     submission,
                     grade):
        """
        This function should take in a Submission object and a Fraction
        holding the calculated grade, returning the new grade.
        """
        pass
