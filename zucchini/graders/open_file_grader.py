import click

from . import PromptGrader, InvalidGraderConfigError

class OpenFileGrader(PromptGrader):
    def __init__(self, file_name, prompts): # type: (str, List[Dict[str, object]]) -> OpenFileGrader
        super(OpenFileGrader, self).__init__(prompts=prompts) # Set up the Prompt Grader first

        self.file_name = file_name

        if not isinstance(self.file_name, str) or len(self.file_name) == 0:
            raise InvalidGraderConfigError("A file_name needs to be specified.")

    def grade(self, submission):
        # Let's get the file from the submission
        file_to_launch = submission.get_absolute_path(self.file_name)
        click.launch(file_to_launch)

        return super(OpenFileGrader, self).grade(submission=submission)
