import json
import os
from fractions import Fraction

from ..submission import BrokenSubmissionError
from ..utils import run_process, PIPE, STDOUT, TimeoutExpired
from ..grades import PartGrade
from . import GraderInterface, Part

"""
Grade a homework using pyLC3 tests
"""


class PyLC3Test(Part):
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

        log = '\n'.join('{0[display-name]}: {0[message]}'.format(test)
                        for test in result if not test['passed'])
        failed = sum(1 for test in result if not test['passed'])

        score = Fraction(len(result) - failed, len(result))
        return PartGrade(score=score, log=log)


class PyLC3Grader(GraderInterface):
    """
    Run a pyLC3 grader and collect the results.
    """

    DEFAULT_TIMEOUT = 30

    def __init__(self, test_file, timeout=None):
        self.test_file = test_file

        if timeout is None:
            self.timeout = self.DEFAULT_TIMEOUT
        else:
            self.timeout = timeout

    def list_prerequisites(self):
        return ['build-essential', 'g++', 'cmake', 'libboost-all-dev',
                'libglib2.0-dev', 'castxml', 'python-pip']

    def list_extra_setup_commands(self):
        return ['pip uninstall -y wheel',  # THANKS ARJUN
                'pip install scikit-build',
                'pip install pyLC3',
                'ldconfig',
                'pip install parameterized']

    def part_from_config_dict(self, config_dict):
        return PyLC3Test.from_config_dict(config_dict)

    def grade(self, submission, path, parts):
        cmdline = ['python3', self.test_file]
        try:
            # Do not mix stderr into stdout because sometimes our friend
            # Roi printStackTrace()s or System.err.println()s, and that
            # will mess up JSON parsing
            process = run_process(cmdline, cwd=path, timeout=self.timeout,
                                  stdout=PIPE, stderr=STDOUT, input='')
        except TimeoutExpired:
            raise BrokenSubmissionError('timeout of {} seconds expired for '
                                        'grader'.format(self.timeout))

        if process.returncode != 0:
            raise BrokenSubmissionError(
                'grader command exited with nonzero exit code {}'
                .format(process.returncode),
                verbose=(process.stdout.decode()
                         if process.stdout else '(no output)'))

        with open(os.path.join(path, 'results.json'), 'r') as json_fp:
            results = json.load(json_fp)

        return [part.grade(results['results'].get(part.test))
                for part in parts]
