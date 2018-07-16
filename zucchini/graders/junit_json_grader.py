import os
import re
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


class JUnitJSONTest(Part):
    __slots__ = ('cls', 'name')

    def __init__(self, test):
        self.test = test
        self.cls, self.name = test.rsplit('.', 1)

    def description(self):
        return '{}.{}'.format(self.cls.rsplit('.', 1)[-1], self.name)


class JUnitJSONGrader(GraderInterface):
    """
    Run a grader jar file and parse the gradelog.json log file the
    creates. This is something Mr. Patrick made just for Zucchini, and
    graders will need to be written to produce this log file.
    """

    DEFAULT_TIMEOUT = 5
    CLASS_REGEX = re.compile(r'\[engine:.*?\]/\[class:(?P<cls>.*?)\]')

    def __init__(self, grader_jar, timeout=None):
        self.grader_jar = grader_jar

        if timeout is None:
            self.timeout = self.DEFAULT_TIMEOUT
        else:
            self.timeout = timeout

    def list_prerequisites(self):
        return ['openjdk-8-jre-headless']

    def part_from_config_dict(self, config_dict):
        return JUnitJSONTest.from_config_dict(config_dict)

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
            cls = self.CLASS_REGEX.match(result['parentId']).group('cls')
            name = result['displayName']
            score = Fraction(result['status'] == 'PASS')
            log = result['failDescription']
            results[(cls, name)] = PartGrade(score=score, log=log)

        return [results[(part.cls, part.name)] for part in parts]
