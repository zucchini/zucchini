import os

import xml.etree.ElementTree
from ..submission import BrokenSubmissionError
from ..utils import run_process, PIPE, STDOUT, TimeoutExpired
from ..grades import PartGrade
from . import Part, GraderInterface


class EnsembleTest(Part):
    __slots__ = ('name')

    def __init__(self, name):
        self.name = name

    def description(self):
        return self.name

    def grade(self, result):
        if result is None:
            msg = ('Results for test not found. Check if there were any'
                   ' internal errors reported. If not, report this as an'
                   ' autograder error to your instructors.')
            return PartGrade(score=0, log=msg)

        failure = result.find('failure')

        if failure is not None:
            log = "\n".join([failure.get('message'), failure.text])
            return PartGrade(score=0, log=log)

        return PartGrade(score=1, log='')

class EnsembleGrader(GraderInterface):
    def __init__(self, test_file, timeout=30):
        self.test_file = test_file
        self.timeout = timeout

    def list_prerequisites(self):
        return []

    def part_from_config_dict(self, config_dict):
        return EnsembleTest.from_config_dict(config_dict)

    def grade(self, submission, path, parts):
        command = ['pytest', self.test_file, '--junitxml', 'report.xml']

        try:
            process = run_process(
                command,
                cwd=path,
                timeout=self.timeout,
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
                'grader command exited with exit code {}'
                .format(process.returncode),
                verbose=process.stdout.decode() if process.stdout else None
            )

        report_xml_path = os.path.join(path, 'report.xml')
        report_xml = xml.etree.ElementTree.parse(report_xml_path)

        return [part.grade(report_xml.find(f'.//testcase[@name=\'{part.name}\']')) for part in parts]
