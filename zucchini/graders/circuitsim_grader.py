import json
from fractions import Fraction

from ..submission import BrokenSubmissionError
from ..utils import run_process, PIPE, TimeoutExpired
from ..grades import PartGrade
from . import GraderInterface, Part

"""
Grade a homework using a CircuitSim grader
"""


class CircuitSimTest(Part):
    __slots__ = ('test',)

    def __init__(self, test):
        self.test = test

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


class CircuitSimGrader(GraderInterface):
    """
    Run a CircuitSim grader based on
    <https://github.com/ausbin/circuitsim-grader-template> and collect
    the results.
    """

    DEFAULT_TIMEOUT = 30

    def __init__(self, grader_jar, test_class, timeout=None):
        self.grader_jar = grader_jar
        self.test_class = test_class

        if timeout is None:
            self.timeout = self.DEFAULT_TIMEOUT
        else:
            self.timeout = timeout

    def list_prerequisites(self):
        # CircuitSim needs JavaFX
        return ['openjdk-8-jre', 'openjfx']

    def needs_display(self):
        # CircuitSim needs JavaFX which needs a display server
        return True

    def part_from_config_dict(self, config_dict):
        return CircuitSimTest.from_config_dict(config_dict)

    def grade(self, submission, path, parts):
        cmdline = ['java', '-jar', self.grader_jar, '--zucchini',
                   self.test_class]
        try:
            # Do not mix stderr into stdout because sometimes our friend
            # Roi printStackTrace()s or System.err.println()s, and that
            # will mess up JSON parsing
            process = run_process(cmdline, cwd=path, timeout=self.timeout,
                                  stdout=PIPE, stderr=PIPE, input='')
        except TimeoutExpired:
            raise BrokenSubmissionError('timeout of {} seconds expired for '
                                        'grader'.format(self.timeout))

        if process.returncode != 0:
            raise BrokenSubmissionError(
                'grader command exited with nonzero exit code {}'
                .format(process.returncode),
                verbose='\n'.join(output_stream.decode()
                                  for output_stream
                                  in [process.stderr, process.stdout]
                                  if output_stream))

        results = json.loads(process.stdout.decode())

        if 'error' in results:
            raise BrokenSubmissionError(results['error'])

        method_results = {result['methodName']:
                          result for result in results['tests']}
        return [part.grade(method_results.get(part.test)) for part in parts]
