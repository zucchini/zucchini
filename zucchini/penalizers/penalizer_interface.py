from abc import ABCMeta, abstractmethod

from ..utils import ConfigDictMixin


class PenalizerInterface(ConfigDictMixin):
    """Penalize a student outside component grades. Example: Late penalties"""

    __metaclass__ = ABCMeta

    def __init__(self):
        """
        The class needs an init method that will take in all of its
        desired options from the config file as keyword args. Required
        options that need to be in the config file should not have
        default values. Optional ones can have default values but still
        need to exist as kwargs. Each of the elements in the options:
        section of the component config of the assignment will be passed
        as a keyword argument during initialization.
        """
        pass

    @abstractmethod
    def adjust_grade(self,
                     submission,
                     grade):
        """
        This function should take in a Submission object and a Fraction
        holding the calculated grade, returning the new grade.
        """
        pass
