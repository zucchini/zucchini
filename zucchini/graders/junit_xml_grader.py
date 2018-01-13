import os
import re
import fnmatch
from fractions import Fraction
import xml.etree.ElementTree
from os import listdir
from os.path import isfile, join

from ..submission import BrokenSubmissionError
from ..utils import run_process, PIPE, STDOUT, TimeoutExpired
from ..grades import PartGrade
from . import GraderInterface, Part

"""
Grade a homework with JUnit tests using Apache Ant formatted XML files
"""


class JUnitXMLTest(Part):
    __slots__ = ('cls', 'name')

    def __init__(self, test):
        self.test = test
        self.cls, self.name = test.rsplit('.', 1)

    def description(self):
        return '{}.{}'.format(self.cls.rsplit('.', 1)[-1], self.name)


class JUnitXMLGrader(GraderInterface):
    """
    Run a gradle test task and parses the resulting XML file, which lists
    successful and failing tests.
    """

    DEFAULT_TIMEOUT = 10
    DEFAULT_RESULT_DIR = 'build/test-results/test'
    CLASS_REGEX = re.compile(r'\[engine:.*?\]/\[class:(?P<cls>.*?)\]')
    DEFAULT_RESULT_MATCHER = 'TEST-*.xml'

    def __init__(self, gradle_exec, gradle_task, timeout=None,
                 xml_result_dir=None, result_matcher=None):
        self.gradle_exec = gradle_exec
        self.gradle_task = gradle_task
        self.timeout = self.DEFAULT_TIMEOUT if timeout is None else timeout
        self.xml_result_dir = self.DEFAULT_RESULT_DIR \
            if xml_result_dir is None else xml_result_dir
        self.result_matcher = self.DEFAULT_RESULT_MATCHER \
            if result_matcher is None else result_matcher

    def list_prerequisites(self):
        return ['sudo apt-get install openjdk-8-jre-headless']

    def part_from_config_dict(self, config_dict):
        return JUnitXMLTest.from_config_dict(config_dict)

    def grade(self, submission, path, parts):
        try:
            # Don't bother keeping the result of running this process
            # because we're not checking the exit code or output, so we
            # don't need it.
            run_process([self.gradle_exec, self.gradle_task],
                        cwd=path,
                        timeout=self.timeout,
                        stdout=PIPE,
                        stderr=STDOUT,
                        shell=True)
        except TimeoutExpired:
            raise BrokenSubmissionError('timeout of {} seconds expired for '
                                        'grader'.format(self.timeout))

        # DO NOT check gradle command return code because a nonzero exit code
        # is returned if tests fail, obviously this is expected
        # if process.returncode != 0:
        #     raise BrokenSubmissionError(
        #         'grader command exited with nonzero exit code {}'
        #         .format(process.returncode),
        #         verbose=process.stdout.decode() if process.stdout else None)

        # goes into xml_result_dir (relative path) and looks for files matching
        # result_matcher
        test_result_path = os.path.join(path, self.xml_result_dir)
        files = [f for f in listdir(test_result_path)
                 if isfile(join(test_result_path, f))
                 and fnmatch.fnmatch(f, self.result_matcher)]

        # processes each XML result file and sends results back
        results = {}
        for f in files:
            test_xml = os.path.join(test_result_path, f)
            e = xml.etree.ElementTree.parse(test_xml).getroot()
            for testcase in e.findall('testcase'):
                failures = testcase.findall('failure')
                cls = testcase.get('classname')
                name = testcase.get('name')
                score = Fraction(1 if not failures else 0)
                log = failures[0].get('message') if failures else ""
                results[(cls, name)] = PartGrade(score=score, log=log)

        return [results[(part.cls, part.name)] for part in parts]
