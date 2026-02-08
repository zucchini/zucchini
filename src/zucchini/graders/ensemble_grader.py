import os

from pathlib import Path
from typing import Literal
import xml.etree.ElementTree
from ..utils import run_command
from ..grades import PartGrade
from . import Part, GraderInterface


class EnsembleTest(Part):
    name: str
    """
    Name of test.

    This corresponds to the function name used by Pytest.
    """

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

class EnsembleGrader(GraderInterface[EnsembleTest]):
    kind: Literal["EnsembleGrader"]

    test_file: Path
    """Name of file to test on."""

    timeout: float = 30
    """Timeout for autograder."""

    @classmethod
    def Part(cls):
        return EnsembleTest
    
    def list_prerequisites(self):
        return []

    def grade(self, submission, path, parts):
        command = ['pytest', self.test_file, '--junitxml', 'report.xml']
        cmd_result = run_command(command, cwd=path, timeout=self.timeout)
        cmd_result.check_returncode({ 0, 1 })

        report_xml_path = os.path.join(path, 'report.xml')
        report_xml = xml.etree.ElementTree.parse(report_xml_path)

        return [part.grade(report_xml.find(f'.//testcase[@name=\'{part.name}\']')) for part in parts]
