import os
import json
import tempfile
from fractions import Fraction

from ..submission import BrokenSubmissionError
from ..utils import run_process, PIPE, STDOUT, TimeoutExpired
from ..grades import PartGrade
from . import GraderInterface, Part

"""
Grade a homework using the classic Java bitwise operators grader
(usually homework 2).
"""


class BitwiseJSONMethod(Part):
    __slots__ = ('method',)

    def __init__(self, method):
        self.method = method

    def description(self):
        return '{}()'.format(self.method)

    def grade(self, jsonResult):

        if jsonResult.get('errorMessage', None):
            return PartGrade(score=Fraction(0), log=jsonResult['errorMessage'])

        violations = jsonResult.get('violations', [])

        # If they violated any rules, boom, zero
        if violations:
            score = Fraction(0)
        else:
            score = Fraction(jsonResult['testsPassed'],
                             jsonResult['testsTotal'])

        log = jsonResult.get('message', '')

        return PartGrade(score=score, deductions=violations, log=log)


class BitwiseJSONGrader(GraderInterface):
    """
    Run the legendary hw2checker.jar and collect results.
    """

    DEFAULT_TIMEOUT = 10

    def __init__(self, grader_jar, source_file, timeout=None):
        self.grader_jar = grader_jar
        self.source_file = source_file

        if timeout is None:
            self.timeout = self.DEFAULT_TIMEOUT
        else:
            self.timeout = timeout

    def list_prerequisites(self):
        return ['sudo apt-get install openjdk-8-jre-headless']

    def part_from_config_dict(self, config_dict):
        return BitwiseJSONMethod.from_config_dict(config_dict)

    def grade(self, submission, path, parts):
        gradelog_fp, gradelog_path = tempfile.mkstemp(prefix='log-',
                                                      suffix='.json', dir=path)
        # Don't leak fds
        os.close(gradelog_fp)

        cmdline = ['java', '-jar', self.grader_jar, '-z', self.source_file,
                   gradelog_path]
        try:
            process = run_process(cmdline, cwd=path, timeout=self.timeout,
                                  stdout=PIPE, stderr=STDOUT, input='')
        except TimeoutExpired:
            raise BrokenSubmissionError('timeout of {} seconds expired for '
                                        'grader'.format(self.timeout))

        if process.returncode != 0:
            raise BrokenSubmissionError(
                'grader command exited with nonzero exit code {}'
                .format(process.returncode),
                verbose=process.stdout.decode() if process.stdout else None)

        with open(gradelog_path) as gradelog_file:
            gradelog = json.load(gradelog_file)

        if gradelog.get('errorMessage', None):
            raise BrokenSubmissionError(gradelog['errorMessage'])

        return [part.grade(gradelog['results'][part.method]) for part in parts]
