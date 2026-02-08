import os
import json
import tempfile
from fractions import Fraction
from typing import Literal
from typing_extensions import override

from ..submission import BrokenSubmissionError
from ..utils import run_command
from ..grades import PartGrade
from . import GraderInterface, Part

"""
Grade a homework using the classic Java bitwise operators grader
"""

class BitwiseJSONMethod(Part):
    """
    A method in the bitwise JSON autograder.
    """

    class_name: str | None = None
    """Name of the class where the method is located."""

    method: str
    """The name of the method."""

    @override
    def description(self):
        return f'{self.class_name}.{self.method}()'

    def grade(self, jsonResults):
        # If the method is missing from the results, they probably
        # didn't implement it.
        if self.method not in jsonResults:
            return PartGrade(score=Fraction(0), log='method not found',
                             deductions=['missing'])
        else:
            jsonResult = jsonResults[self.method]

        if jsonResult.get('errorMessage', None):
            return PartGrade(score=Fraction(0), log=jsonResult['errorMessage'])

        violations: list[str] = jsonResult.get('violations', [])

        # If they violated any rules, boom, zero
        if violations:
            score = Fraction(0)
        else:
            score = Fraction(jsonResult['testsPassed'],
                             jsonResult['testsTotal'])

        log = jsonResult.get('message', '')

        return PartGrade(score=score, deductions=violations, log=log)

class BitwiseJSONGrader(GraderInterface[BitwiseJSONMethod]):
    """
    Run the legendary hw2checker.jar and collect results.
    """
    
    kind: Literal["BitwiseJSONGrader"]
    
    grader_jar: str
    """
    Filename for the autograder JAR this autograder should run.
    """

    source_file: str
    """
    The source file we're autograding (this will be the user's file).
    """

    timeout: float = 10
    """
    Timeout (in seconds) before the autograder aborts operation.
    """

    @override
    @classmethod
    def Part(cls):
        return BitwiseJSONMethod
    
    @override
    def list_prerequisites(self):
        return ['openjdk-8-jre-headless']

    def class_name(self):
        """Return the class name of this file"""
        return self.source_file.rsplit('.', maxsplit=1)[0]
    
    @override
    def part_from_config_dict(self, config_dict):
        return BitwiseJSONMethod(class_name=self.class_name(), **config_dict)

    @override
    def grade(self, submission, path, parts):
        gradelog_fp, gradelog_path = tempfile.mkstemp(prefix='log-',
                                                      suffix='.json', dir=path)
        # Don't leak fds
        os.close(gradelog_fp)

        # Run command:
        cmdline = ['java', '-jar', self.grader_jar, '-z', self.source_file, gradelog_path]
        cmd_result = run_command(cmdline, cwd=path, timeout=self.timeout)
        cmd_result.check_returncode()

        with open(gradelog_path) as gradelog_file:
            gradelog = json.load(gradelog_file)

        if gradelog.get('errorMessage', None):
            raise BrokenSubmissionError(gradelog['errorMessage'])

        return [part.grade(gradelog['results']) for part in parts]
