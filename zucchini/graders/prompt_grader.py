import collections
from fractions import Fraction

import click

from . import GraderInterface, InvalidGraderConfigError, SubcomponentGrade
from ..utils import ConfigDictMixin


class Prompt(ConfigDictMixin):
    def __init__(self, text, answer_type, weight, answer_range=None):
        self.text = text
        self.answer_type = None

        if answer_type == bool or answer_type == "bool":
            self.answer_type = bool
            self.range_low = 0
            self.range_high = 1
        elif answer_type == int or answer_type == "int":
            self.answer_type = int
        else:
            raise InvalidGraderConfigError("Invalid answer_type: %s. Only bool"
                                           " and int are supported." %
                                           answer_type)

        self.weight = weight
        if type(self.weight) != int:
            raise InvalidGraderConfigError("Weight must be an integer.")

        if self.answer_type == int:  # In this case we also need a range
            if answer_range is None:
                raise InvalidGraderConfigError("An answer_range needs to be "
                                               "specified for int prompts.")

            if not isinstance(answer_range, collections.Iterable):
                raise InvalidGraderConfigError("The answer_range needs to be a"
                                               " list of two elements: start"
                                               " and end.")

            self.answer_range = tuple(answer_range)

            if len(self.answer_range) != 2:
                raise InvalidGraderConfigError("Prompt score answer_range "
                                               "should consist only of two "
                                               "elements.")

            for element in self.answer_range:
                if type(element) != int:
                    raise InvalidGraderConfigError(
                        "Types of the answer_range elements need to be int.")

            self.range_low, self.range_high = self.answer_range
            self.answer_type = click.IntRange(self.range_low, self.range_high)

    def grade(self):
        """Prompt the user and return a SubcomponentGrade for this prompt"""

        response = click.prompt(text=self.text, type=self.answer_type)
        score = Fraction(response - self.range_low,
                         self.range_high - self.range_low)
        return SubcomponentGrade(id=self.text, score=score,
                                 logs='response: {}'.format(response))


class PromptGrader(GraderInterface):
    def __init__(self,
                 prompts):  # type: (List[Dict[str, object]]) -> PromptGrader
        self.prompts = []

        # Check if our prompts are a list
        if not isinstance(prompts, collections.Iterable):
            raise InvalidGraderConfigError("The prompts option needs to be a "
                                           "list of Prompt dictionaries.")

        for prompt_options in prompts:
            self.prompts.append(Prompt.from_config_dict(prompt_options))

    def grade(self, submission, path):
        # The submission is not relevant here, so don't use it
        return [prompt.grade() for prompt in self.prompts]
