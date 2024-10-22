import re

import xml.etree.ElementTree
from ..submission import BrokenSubmissionError
from ..utils import run_process, PIPE, STDOUT, TimeoutExpired
from ..grades import PartGrade
from . import Part, GraderInterface

class CriterionTest(Part):
    __slots__ = ('name', 'suite', 'test')

    def __init__(self, name, suite, test):
        self.name = name
        self.suite = suite
        self.test = test
    
    def description(self):
        return self.name
    
    def grade(self, path):
        command = ['./tests', f'--filter={self.suite}/{self.test}', '--ascii']

        try:
            process = run_process(command, cwd=path, stdout=PIPE, stderr=STDOUT, timeout=60)
        except TimeoutExpired:
            raise BrokenSubmissionError("timeout of 60 seconds expired for grader")
        
        result = process.stdout.decode()

        if result is None:
            msg = ('Results for test not found. Check if there were any'
                   ' internal errors reported. If not, report this as an'
                   ' autograder error to your instructors.')
            return PartGrade(score=0, log=msg)
        
        pattern = r"Tested:\s*(\d+)\s*\|\s*Passing:\s*(\d+)"

        matches = re.search(pattern, result)

        if not matches:
            return PartGrade(score=0, log="Could not parse autograder output")
        
        total, passing = int(matches.group(1)), int(matches.group(2))

        if total == 0:
            return PartGrade(score=0, log="No test cases were found")

        if total == passing:
            return PartGrade(score=1, log="")
        
        log_line_pattern = r"^\s*\[----\].*"
        matches = re.findall(log_line_pattern, result, re.MULTILINE)

        return PartGrade(score=passing / total, log="\n".join(matches))

class CriterionGrader(GraderInterface):
    def list_prerequisites(self):
        return []

    def part_from_config_dict(self, config_dict):
        return CriterionTest.from_config_dict(config_dict)

    def grade(self, submission, path, parts):
        command = ['make', 'tests']

        try:
            process = run_process(
                command,
                cwd=path,
                timeout=30,
                stdout=PIPE,
                stderr=STDOUT,
                input=''
            )
        except TimeoutExpired:
            raise BrokenSubmissionError(
                "timeout of {} seconds expired for grader"
                .format(self.timeout)
            )

        if process.returncode != 0 and process.returncode != 1:
            raise BrokenSubmissionError(
                'grader command exited with exit code {}\n'
                .format(process.returncode),
                verbose=process.stdout.decode() if process.stdout else None
            )

        return [part.grade(path) for part in parts]