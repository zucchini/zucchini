import re
from fractions import Fraction

from ..grades import PartGrade
from ..utils import PIPE, STDOUT, run_process
from . import Part, ThreadedGrader


class LC3ToolsLegacyTest(Part):
    __slots__ = "name"

    def __init__(self, name):
        self.name = name

    def description(self):
        return self.name

    @staticmethod
    def format_cmd(cmd, **kwargs):
        return [arg.format(**kwargs) for arg in cmd]

    @staticmethod
    def test_error_grade(message):
        return PartGrade(Fraction(0), deductions=("error",), log=message)

    def grade(self, path, grader):
        grade = PartGrade(Fraction(1), log="")

        run_cmd = self.format_cmd(grader.cmdline, testcase=self.name)

        process = run_process(run_cmd, cwd=path, stdout=PIPE, stderr=STDOUT)

        if process.returncode != 0:
            return self.test_error_grade(
                "tester exited with {} != 0:\n{}".format(
                    process.returncode,
                    (
                        process.stdout.decode()
                        if process.stdout is not None
                        else "(no output)"
                    ),
                )
            )

        out_contents = process.stdout.decode()
        out_contents = re.sub(r"\(\+.*pts\)", "", out_contents)
        results = "".join(out_contents.strip().splitlines(keepends=True)[:-1])
        grade.log += results

        try:
            summary = out_contents.splitlines()[-1]
            score = summary.replace("/", " ").split()[3:5]
            score[0] = Fraction(float(score[0]))
            score[1] = Fraction(float(score[1]))
            grade.score *= Fraction(score[0], score[1])
        except (ValueError, IndexError):
            return self.test_error_grade(
                "Could not assemble file: \n{}".format(
                    process.stdout.decode()
                    if process.stdout is not None
                    else "(no output)"
                )
            )
        return grade


class LC3ToolsLegacyGrader(ThreadedGrader):
    """
    Run a LC3Tools grader and collect the results.
    """

    DEFAULT_TIMEOUT = 30

    def __init__(self, test_file, asm_file, timeout=None, num_threads=None):

        super(LC3ToolsLegacyGrader, self).__init__(num_threads)
        self.test_file = test_file
        self.asm_file = asm_file

        self.cmdline = [
            "./" + self.test_file,
            self.asm_file,
            "--test-filter={testcase}",
            "--tester-verbose",
            "--asm-print-level=3",
        ]

        self.timeout = self.DEFAULT_TIMEOUT if timeout is None else timeout

    def list_prerequisites(self):
        return []

    def part_from_config_dict(self, config_dict):
        return LC3ToolsLegacyTest.from_config_dict(config_dict)

    def grade_part(self, part, path, submission):
        return part.grade(path, self)

    def grade(self, submission, path, parts):

        return super(LC3ToolsLegacyGrader, self).grade(submission, path, parts)
