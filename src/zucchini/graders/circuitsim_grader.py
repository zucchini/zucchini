import json
from fractions import Fraction
from pathlib import Path
import subprocess
from typing import Literal

from ..submission import BrokenSubmissionError
from ..utils import run_command
from ..grades import PartGrade
from . import GraderInterface, Part

"""
Grade a homework using a CircuitSim grader
"""


class CircuitSimTest(Part):
    test: str
    """
    Name of test.
    This corresponds to the method name of the JUnit test.
    """
    
    def description(self):
        return self.test

    def grade(self, result):
        if result is None:
            msg = ('Results for test not found. Check if there were any'
                   ' internal errors reported. If not, report this as an'
                   ' autograder error to your instructors.')
            return PartGrade(score=Fraction(0), log=msg)

        log = '\n'.join('{}: {}'.format(
            failure['displayName'],
            failure.get('message', '(no details, sorry)'))
            for failure in result['partialFailures'])
        partialFailures = len(result['partialFailures'])
        if partialFailures < result['failed']:
            log += '\n[omitted {} more failures]' \
                   .format(result['failed'] - partialFailures)

        score = Fraction(result['total'] - result['failed'], result['total'])
        return PartGrade(score=score, log=log)

class CircuitSimGrader(GraderInterface[CircuitSimTest]):
    """
    Run a CircuitSim grader based on
    <https://github.com/ausbin/circuitsim-grader-template> and collect
    the results.
    """
    kind: Literal["CircuitSimGrader"]

    grader_jar: Path
    """
    Filename for the autograder JAR this autograder should run.
    """

    test_class: str
    """
    Name of class where tests are located.
    """

    timeout: float = 30
    """
    Timeout (in seconds) before the autograder aborts operation.
    """

    @classmethod
    def Part(cls):
        return CircuitSimTest
    
    def list_prerequisites(self):
        # CircuitSim needs JavaFX
        return ['openjdk-8-jre', 'openjfx']

    def needs_display(self):
        # CircuitSim needs JavaFX which needs a display server
        return True

    def grade(self, submission, path, parts):
        cmdline = ['java', '-jar', self.grader_jar, '--zucchini',
                   self.test_class]
        
        # Do not mix stderr into stdout because sometimes our friend
        # Roi printStackTrace()s or System.err.println()s, and that
        # will mess up JSON parsing
        cmd_result = run_command(cmdline, cwd=path, timeout=self.timeout, stderr=subprocess.PIPE)
        cmd_result.check_returncode()
        results = json.loads(cmd_result.stdout)

        if 'error' in results:
            raise BrokenSubmissionError(results['error'])

        method_results = {result['methodName']:
                          result for result in results['tests']}
        return [part.grade(method_results.get(part.test)) for part in parts]
