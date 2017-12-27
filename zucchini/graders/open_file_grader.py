import os

import click

from . import PromptGrader, InvalidGraderConfigError
from ..utils import sanitize_path


class OpenFileGrader(PromptGrader):
    def __init__(self, file_name, prompts):
        # type: (str, List[Dict[str, object]]) -> OpenFileGrader
        # Set up the Prompt Grader first
        super(OpenFileGrader, self).__init__(prompts=prompts)

        if not isinstance(file_name, str) or len(file_name) == 0:
            raise InvalidGraderConfigError(
                "A file_name needs to be specified.")
        else:
            self.file_name = sanitize_path(file_name)

    def grade(self, submission, path):
        # Let's get the file from the submission
        file_to_launch = os.path.join(path, self.file_name)
        click.launch(file_to_launch)

        return super(OpenFileGrader, self).grade(submission=submission,
                                                 path=path)
