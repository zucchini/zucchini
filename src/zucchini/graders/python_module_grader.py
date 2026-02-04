import sys
import os.path
from importlib import import_module
from fractions import Fraction

from ..submission import BrokenSubmissionError
from ..grades import PartGrade
from . import GraderInterface, Part

"""
Grade a homework using a custom python module in grading-files/. This
way you don't need to exec() anything and can grade a homework from the
comfort of your own cozy Python function.
"""


class PythonModulePart(Part):
    __slots__ = ('id', 'name')

    def __init__(self, id, name):
        self.id = id
        self.name = name

    def description(self):
        return self.name

    def grade(self, result):
        if result is None:
            score = Fraction(0)
            log = "missing part id in result!"
        elif isinstance(result, Exception):
            score = Fraction(0)
            log = 'grading part threw exception: {}'.format(result)
        # Should be a fractions.Fraction
        else:
            score = Fraction(result)
            log = ''

        return PartGrade(score=score, log=log)


class PythonModuleGrader(GraderInterface):
    """
    Run a Python module and collect the results. Very basic, will
    probably need to be expanded down the road.

    The module needs to be in grading-files/, and the function set by
    `function' in zucchini.yml needs to return a dict mapping part_id ->
    fractions.Fraction (or -> Exception if something went wrong).
    """

    def __init__(self, module, function, student_file):
        self.module = module
        self.function = function
        self.student_file = student_file

    def part_from_config_dict(self, config_dict):
        return PythonModulePart.from_config_dict(config_dict)

    def grade(self, submission, path, parts):
        old_sys_path = sys.path[:]
        sys.path.append(path)

        try:
            return self._grade(submission, path, parts)
        finally:
            sys.path = old_sys_path

    def _grade(self, submission, path, parts):
        try:
            autograder_module = import_module(self.module)
        except Exception as err:
            raise BrokenSubmissionError("error importing module `{}': {}"
                                        .format(self.module, str(err)))

        autograder_func = getattr(autograder_module, self.function)

        student_file_path = os.path.join(path, self.student_file)

        try:
            results = autograder_func(student_file_path)
        except Exception as err:
            raise BrokenSubmissionError("autograder function choked: {}"
                                        .format(str(err)))

        return [part.grade(results.get(part.id)) for part in parts]
