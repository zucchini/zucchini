from abc import ABCMeta, abstractmethod

from ..utils import ConfigDictMixin


class GraderInterface(ConfigDictMixin):
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

    def list_prerequisites(self):  # type: () -> List[str]
        """
        This function should return a list of commands required to
        install this grader's prerequisites on an Ubuntu 16.04 machine.
        """
        return []

    def is_interactive(self):  # type: () -> bool
        """
        Return True if and only if this grader will produce command-line
        prompts.
        """
        return False

    @abstractmethod
    def part_from_config_dict(self, config_dict):  # type: (dict) -> Part
        """
        Convert and validate a dictionary parsed from the `parts'
        section of a component configuration to a Part instance.
        """
        pass

    @abstractmethod
    def grade(self,
              submission,  # type: Submission
              path,        # type: str
              parts):      # type: List[Part]
        # type: (...) -> List[PartGrade]
        """
        This function should take in a Submission object and a path,
        where the path can be assumed to be the root of the submission
        directory (it will be a directory where the grading manager has
        copied the required files for this grader); then complete the
        grading on it, and then return a list of kasjdfkasjdfkj
        instances containing the result for each subcomponent.
        """
        pass


class Part(ConfigDictMixin):
    """
    Represent a `part' of grading which has its own weight and its own
    score: one prompt question, one unit test, etc.
    """

    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self):
        """
        Subclasses should override this method and include
        required/optional config keys as arguments. Then you can simply
        return MyPartSubclass.from_config_dict(config_dict) in
        MyGrader.part_from_config_dict().
        """
        pass

    @abstractmethod
    def description(self):
        """
        Return a human-friendly description for this part. Used in grade
        breakdowns and logs.
        """
        pass
