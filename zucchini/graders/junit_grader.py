import os
import json
from fractions import Fraction

from ..submission import BrokenSubmissionError
from ..utils import run_process, PIPE, STDOUT, TimeoutExpired
from ..grades import PartGrade
from . import GraderInterface, Part

"""
Grade a homework with JUnit tests using the log format created by
Patrick (thanks Patrick!)
"""


class JUnitTest(Part):
    __slots__ = ('name')

    def __init__(self, name):
        self.name = name

    def description(self):
        return self.name


class JUnitGrader(GraderInterface):
    DEFAULT_TIMEOUT = 5

    def __init__(self, grader_jar, timeout=None):
        self.grader_jar = grader_jar

        if timeout is None:
            self.timeout = self.DEFAULT_TIMEOUT
        else:
            self.timeout = timeout

    def list_prerequisites(self):
        return ['sudo apt-get install openjdk-8-jre-headless']

    def part_from_config_dict(self, config_dict):
        return JUnitTest.from_config_dict(config_dict)

    def grade(self, submission, path, parts):
        try:
            process = run_process(['java', '-jar', self.grader_jar],
                                  cwd=path,
                                  timeout=self.timeout,
                                  stdout=PIPE,
                                  stderr=STDOUT)
        except TimeoutExpired:
            raise BrokenSubmissionError('timeout of {} seconds expired for '
                                        'grader'.format(self.timeout))

        if process.returncode != 0:
            raise BrokenSubmissionError(
                'grader command exited with nonzero exit code {}'
                .format(process.returncode),
                verbose=process.stdout.decode() if process.stdout else None)

        gradelog_path = os.path.join(path, 'gradelog.json')

        if not os.path.exists(gradelog_path):
            raise BrokenSubmissionError('gradelog.json does not exist')

        with open(gradelog_path) as gradelog_file:
            gradelog = json.load(gradelog_file)

        results = {}

        for result in gradelog:
            name = result['displayName']
            score = Fraction(result['status'] == 'PASS')
            log = result['failDescription']
            results[name] = PartGrade(score=score, log=log)

        return [result[part.name] for part in parts]
