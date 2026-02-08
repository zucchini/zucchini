import json
import os
import re
import tempfile
from typing import Literal

from ..submission import BrokenSubmissionError
from ..utils import ShlexCommand, run_process, PIPE, STDOUT, TimeoutExpired
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

    def description(self):
        return self.name
    
    def grade(self, path, grader):
        resultfile_fd, resultfile_fp = tempfile.mkstemp(prefix="log-", dir=path)
        os.close(resultfile_fd)

        flags = [
            "--timeout", str(grader.single_timeout),
            f"--filter={self.suite}/{self.test}",
            f"--json={resultfile_fp}"
        ]

        command = ['./tests', *flags]
        valgrind_cmd = None
        if grader.valgrind_cmd is not None:
            valgrind_cmd = grader.valgrind_cmd + flags

        # Run one test without Valgrind:
        try:
            process = run_process(command, cwd=path, stdout=PIPE, stderr=STDOUT, timeout=grader.total_timeout)
        except TimeoutExpired:
            raise BrokenSubmissionError(f'grader timed out after {grader.total_timeout} seconds')
        
        result = process.stdout.decode(errors='backslashreplace')

        if result is None:
            msg = ('Results for test not found. Check if there were any'
                   ' internal errors reported. If not, report this as an'
                   ' autograder error to your instructors.')
            return PartGrade(score=0, log=msg)
        
        with open(resultfile_fp, "r") as f:
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
                try:
                    process = run_process(valgrind_cmd, cwd=path, stdout=PIPE, stderr=STDOUT, timeout=grader.total_timeout)
                except TimeoutExpired:
                    raise BrokenSubmissionError(f'grader timed out after {grader.total_timeout} seconds')
                result = process.stdout.decode(errors='backslashreplace')

                if re.search(r"^==\d+==.*$", result, re.MULTILINE): # Valgrind failed
                    return PartGrade(1 - self.valgrind_deduction, log=result)
            return PartGrade(score=1, log="")
        
        log_line_pattern = r"^\s*\[(?:----|FAIL)\].*"
        log = "\n".join(re.findall(log_line_pattern, result, re.MULTILINE))
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
    
    @classmethod
    def Part(cls):
        return CriterionTest
    
    def list_prerequisites(self):
        return []
    
    def grade_part(self, part, path, submission):
        return part.grade(path, self)

    def grade(self, submission, path, parts):
        command = ['make', 'tests']

        try:
            process = run_process(
                command,
                cwd=path,
                timeout=self.total_timeout,
                stdout=PIPE,
                stderr=STDOUT,
                input=''
            )
        except TimeoutExpired:
            raise BrokenSubmissionError(
                "timeout of {} seconds expired for grader"
                .format(self.total_timeout)
            )

        if process.returncode != 0 and process.returncode != 1:
            raise BrokenSubmissionError(
                'grader command exited with exit code {}\n'
                .format(process.returncode),
                verbose=process.stdout.decode(errors='backslashreplace') if process.stdout else None
            )

        return super(CriterionGrader, self).grade(submission, path, parts)