import re

from ..submission import BrokenSubmissionError
from ..utils import run_process, PIPE, STDOUT, TimeoutExpired
from ..grades import PartGrade, Fraction
from . import Part, ThreadedGrader

class CriterionTest(Part):
    __slots__ = ('name', 'suite', 'test')

    def __init__(self, name, suite, test, valgrind_deduction="1/2"):
        self.name = name
        self.suite = suite
        self.test = test
        self.valgrind_deduction = Fraction(valgrind_deduction)
    
    def description(self):
        return self.name
    
    def grade(self, path, grader):
        command = ['./tests', f'--filter={self.suite}/{self.test}']
        valgrind_cmd = grader.valgrind_cmd + [f'--filter={self.suite}/{self.test}']

        try:
            process = run_process(valgrind_cmd if valgrind_cmd else command, cwd=path, stdout=PIPE, stderr=STDOUT, timeout=60)
        except TimeoutExpired:
            raise BrokenSubmissionError('grader timed out after 60 seconds')
        
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

        if valgrind_cmd and process.returncode != 0:
            return PartGrade(passing / total * (1 - self.valgrind_deduction), log=result)

        if total == passing:
            return PartGrade(score=1, log="")
        
        log_line_pattern = r"^\s*\[----\].*"
        matches = re.findall(log_line_pattern, result, re.MULTILINE)

        return PartGrade(score=passing / total, log="\n".join(matches))

class CriterionGrader(ThreadedGrader):
    def __init__(self, valgrind_cmd=None):
        super(CriterionGrader, self).__init__(None)
        self.valgrind_cmd = valgrind_cmd.split(" ")

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

        return super(CriterionGrader, self).grade(submission, path, parts)