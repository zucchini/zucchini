from pathlib import Path
import tempfile
from typing import Literal
from typing_extensions import override

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

    @override
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

    @override
    def list_prerequisites(self):
        return []

    @override
    def Part(self, _cd):
        return EnsembleTest
    
    @override
    def grade(self, submission, path, parts):
        result_file = tempfile.NamedTemporaryFile(prefix='zlog-', suffix='.xml', dir=path, delete=True)
        result_file.close() # Close file to allow subprocess to write
        
        command = ['pytest', self.test_file, '--junitxml', result_file.name]
        cmd_result = run_command(command, cwd=path, timeout=self.timeout)
        cmd_result.check_returncode({ 0, 1 })

        report_xml = xml.etree.ElementTree.parse(result_file.name)

        return [part.grade(report_xml.find(f'.//testcase[@name=\'{part.name}\']')) for part in parts]
