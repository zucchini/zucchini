class InvalidGraderConfigError(ValueError):
    """
    Exception indicating the Zucchini config file
    had a misconfigured grader backend.
    """
    pass

class InvalidPenalizerConfigError(ValueError):
    """
    Exception indicating the Zucchini config file
    had a misconfigured penalizer.
    """
    pass

class BrokenSubmissionError(Exception):
    """
    Exception indicating the submitted file could not be autograded
    (it is unable to be run or an error occurred while running).
    """
    def __init__(self, message: str, verbose: str | None = None):
        super(BrokenSubmissionError, self).__init__(message)
        self.message = message
        self.verbose = verbose