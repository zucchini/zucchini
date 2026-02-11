class ZucchiniError(ValueError):
    """
    Any error which occurs when calling Zucchini.

    This could be misconfiguration on the autograder side or
    broken files on the user side.
    """
    def __init__(self, message: str, verbose: str | None = None, is_it_autograders_fault: bool = False):
        super().__init__(message)
        self.message = message
        self.verbose = verbose
        self.is_it_autograders_fault = is_it_autograders_fault

    @classmethod
    def _validate(cls, data: "dict | ZucchiniError"):
        if isinstance(data, ZucchiniError):
            return data
        
        error = data["error"]
        verbose = data["verbose"]
        autograder = data["autograder"]
        if autograder:
            return BrokenAutograderError(error, verbose)
        else:
            return BrokenSubmissionError(error, verbose)
        
    def _serialize(self):
        return {
            "error": self.message,
            "verbose": self.verbose,
            "autograder": self.is_it_autograders_fault
        }

class BrokenAutograderError(ZucchiniError):
    """
    Any error which occurs due to the autograder being misconfigured.
    """
    def __init__(self, message: str, verbose: str | None = None):
        super().__init__(message, verbose, is_it_autograders_fault=True)

class InvalidGraderConfigError(BrokenAutograderError):
    """
    Exception indicating the Zucchini config file
    had a misconfigured grader backend.
    """
    pass

class InvalidPenalizerConfigError(BrokenAutograderError):
    """
    Exception indicating the Zucchini config file
    had a misconfigured penalizer backend.
    """
    pass

class BrokenSubmissionError(ZucchiniError):
    """
    Exception indicating the submitted file could not be autograded
    (it is unable to be run or an error occurred while running).
    """
    def __init__(self, message: str, verbose: str | None = None):
        super().__init__(message, verbose, is_it_autograders_fault=False)