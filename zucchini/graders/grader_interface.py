from abc import ABCMeta, abstractmethod


class GraderInterface:
    __metaclass__ = ABCMeta

    # The class needs an init method that will take in all of its desired
    # options from the config file as keyword args.
    # Required options that need to be in the config file should not have
    # default values.
    # Optional ones can have default values but still need to exist as kwargs.
    # Each of the elements in the options: section of the component config of
    # the assignment will be passed as a keyword argument during
    # initialization.

    @staticmethod
    def list_prerequisites():  # type: () -> List[str]
        """This function should return a list of commands required to install
        this grader's prerequisites on an Ubuntu 14.04 machine."""
        return []

    @abstractmethod
    def grade(self, submission):  # type: (Submission) -> int
        """This function should take in a Submission object, complete the
        grading on it, and return the submission's score."""
