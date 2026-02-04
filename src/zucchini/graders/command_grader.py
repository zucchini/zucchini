import shlex

from . import PromptGrader, InvalidGraderConfigError
from ..utils import run_process


class CommandGrader(PromptGrader):
    def __init__(self, command):
        # Set up the Prompt Grader first
        super(CommandGrader, self).__init__()

        if not isinstance(command, str) or not command:
            raise InvalidGraderConfigError(
                "A command needs to be specified.")
        else:
            self.command = shlex.split(command)

    def grade(self, submission, path, parts):
        # Let's get the file from the submission
        run_process(self.command, cwd=path)
        return super(CommandGrader, self).grade(submission=submission,
                                                path=path, parts=parts)
