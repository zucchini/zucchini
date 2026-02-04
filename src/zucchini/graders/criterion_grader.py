import json
import os
import re
import shlex
import tempfile

from ..submission import BrokenSubmissionError
from ..utils import run_process, PIPE, STDOUT, TimeoutExpired
from ..grades import PartGrade, Fraction
from . import Part, ThreadedGrader

class CriterionTest(Part):
    __slots__ = ('name', 'suite', 'test')

    def __init__(self, name, suite, test="*", valgrind_deduction="1/2"):
        self.name = name
        self.suite = suite
        self.test = test
        self.valgrind_deduction = Fraction(valgrind_deduction)
    
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

class CriterionGrader(ThreadedGrader):
    def __init__(self, valgrind_cmd: "str | None" = None, total_timeout: float = 60, single_timeout: float = 3):
        super(CriterionGrader, self).__init__(None)

        # If enabled, use Valgrind:
        self.valgrind_cmd = None
        if valgrind_cmd is not None:
            self.valgrind_cmd = shlex.split(valgrind_cmd)

        # Configure timeout
        self.single_timeout = float(single_timeout)
        self.total_timeout = float(total_timeout)

    def list_prerequisites(self):
        return []

    def part_from_config_dict(self, config_dict):
        return CriterionTest.from_config_dict(config_dict)
    
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