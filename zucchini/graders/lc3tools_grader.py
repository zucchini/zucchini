import json
from fractions import Fraction

from ..grades import PartGrade
from ..submission import BrokenSubmissionError
from ..utils import PIPE, TimeoutExpired, run_process
from . import GraderInterface, Part

"""
Grade a homework using a LC3tools grader on the new testing framework
(API_VER 2110)
"""


class LC3ToolsTest(Part):
    __slots__ = ("test",)

    def __init__(self, test):
        self.test = test

    def description(self):
        return self.test

    def grade(self, result):
        if result is None:
            msg = (
                "Results for test not found. Check if there were any "
                "assembler erros when assembling this file on lc3tools. If not"
                ", report this as an autograder error to the instructors."
            )
            return PartGrade(score=Fraction(0), log=msg)

        # display potentially helpful output if test failed
        partialFailures = len(result["partialFailures"])
        log = result["output"] if partialFailures else ""

        log += "\n".join(
            "--{}: {}".format(failure["displayName"], failure["message"])
            for failure in result["partialFailures"]
        )

        if partialFailures < result["failed"]:
            log += "\n[omitted {} more failures]".format(
                result["failed"] - partialFailures
            )

        score = Fraction(result["total"] - result["failed"], result["total"])
        return PartGrade(score=score, log=log)


class LC3ToolsGrader(GraderInterface):
    """
    Run a LC3Tools test executable, which can output json with the new
    testing framework (much more reliable than regex). Pretty heavily inspired
    by the CircuitSim and PyLC3 graders.
    """

    DEFAULT_TIMEOUT = 30

    def __init__(self, test_file, asm_file, timeout=None):
        self.test_file = test_file
        self.asm_file = asm_file

        self.timeout = self.DEFAULT_TIMEOUT if timeout is None else timeout

    def list_prerequisites(self):
        # test executables are already built
        return []

    def part_from_config_dict(self, config_dict):
        return LC3ToolsTest.from_config_dict(config_dict)

    def grade(self, submission, path, parts):
        cmdline = [
            "./" + self.test_file,
            self.asm_file,
            "--json-output",
            "--asm-print-level=3",
        ]
        try:
            # Do not mix stderr into stdout because sometimes our friend
            # Roi printStackTrace()s or System.err.println()s, and that
            # will mess up JSON parsing
            process = run_process(
                cmdline,
                cwd=path,
                timeout=self.timeout,
                stdout=PIPE,
                stderr=PIPE,
                input="",
            )
        except TimeoutExpired:
            raise BrokenSubmissionError(
                "timeout of {} seconds expired for grader".format(self.timeout)
            )

        if process.returncode != 0:
            raise BrokenSubmissionError(
                "grader command exited with nonzero exit code {}".format(
                    process.returncode
                ),
                verbose="\n".join(
                    output_stream.decode()
                    for output_stream in [process.stderr, process.stdout]
                    if output_stream
                ),
            )

        results = json.loads(process.stdout.decode())

        if "error" in results:
            raise BrokenSubmissionError(results["error"])

        method_results = {res["testName"]: res for res in results["tests"]}
        return [part.grade(method_results.get(part.test)) for part in parts]
