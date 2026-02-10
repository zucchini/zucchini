import json
import re
import tempfile
from typing import Literal
from typing_extensions import override

from ..utils import ShlexCommand, run_command
from ..grades import PartGrade, Fraction
from . import Part, ThreadedGrader

class CriterionTest(Part):
    name: str
    """
    Name of test.

    This is a descriptor which will be displayed on Gradescope.
    """

    suite: str
    """
    The suite identifier.
    """

    test: str = "*"
    """
    The test identifier.

    This is the identifier used to distinguish test cases within a suite.
    """

    valgrind_deduction: Fraction = Fraction(1, 2)

    @override
    def description(self):
        return self.name
    
    def grade(self, path, grader):
        result_file = tempfile.NamedTemporaryFile(prefix='zlog-', suffix='.json', dir=path, delete=True)
        result_file.close() # Close file to allow subprocess to write

        flags = [
            "--timeout", str(grader.single_timeout),
            f"--filter={self.suite}/{self.test}",
            f"--json={result_file.name}"
        ]

        command = ['./tests', *flags]
        valgrind_cmd = None
        if grader.valgrind_cmd is not None:
            valgrind_cmd = grader.valgrind_cmd + flags

        # Run tests without Valgrind:
        cmd_result = run_command(command, cwd=path, timeout=grader.total_timeout)
        out = cmd_result.stdout

        with open(result_file.name, "r") as f:
            try:
                report_data = json.load(f)
            except json.JSONDecodeError:
                return PartGrade(score=0, log="Cannot parse result JSON")
        passing = report_data["passed"]
        failing = report_data["failed"]
        total = passing + failing
        
        if total == 0:
            return PartGrade(score=0, log="No test cases were found")

        if total == passing:
            # Standard autograder passed, so check Valgrind:
            # Check Valgrind test:
            if valgrind_cmd is not None:
                cmd_result = run_command(valgrind_cmd, cwd=path, timeout=grader.total_timeout)
                out = cmd_result.stdout

                if re.search(r"^==\d+==.*$", out, re.MULTILINE): # Valgrind failed
                    return PartGrade(score=1 - self.valgrind_deduction, log=out)
            return PartGrade(score=1, log="")
        
        log_line_pattern = r"^\s*\[(?:----|FAIL)\].*"
        log = "\n".join(re.findall(log_line_pattern, out, re.MULTILINE))
        deduct_factor = 1 # factor added to make Valgrind failures fairer
        if valgrind_cmd is not None:
            log += "\n\nValgrind skipped due to failed test."
            deduct_factor *= 1 - self.valgrind_deduction

        return PartGrade(score=(passing / total) * deduct_factor, log=log)

class CriterionGrader(ThreadedGrader[CriterionTest]):
    kind: Literal["CriterionGrader"]

    single_timeout: float = 3
    """Timeout for a single test."""

    total_timeout: float = 60
    """Timeout for the autograder overall."""

    valgrind_cmd: ShlexCommand | None = None
    """Command to use to run Valgrind."""
    
    @override
    @classmethod
    def Part(cls):
        return CriterionTest
    
    @override
    def list_prerequisites(self):
        return []
    
    @override
    def grade_part(self, part, path, submission):
        return part.grade(path, self)

    @override
    def grade(self, submission, path, parts):
        # Compile program:
        cmd_result = run_command(["make", "tests"], cwd=path, timeout=self.total_timeout)
        cmd_result.check_returncode({ 0, 1 })

        # Run each part:
        return super(CriterionGrader, self).grade(submission, path, parts)