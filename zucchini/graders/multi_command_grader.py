import shlex
from fractions import Fraction

from ..submission import BrokenSubmissionError
from ..utils import run_process, PIPE, STDOUT, TimeoutExpired
from ..grades import PartGrade
from . import GraderInterface, Part

"""
Grade a homework by execuing a bunch of commands
"""


class Command(Part):
    """A command to execute"""

    __slots__ = ('summary', 'command')

    def __init__(self, summary, command):
        self.summary = summary
        self.command = shlex.split(command)

    def description(self):
        return self.summary

    def grade(self, path, timeout):
        try:
            process = run_process(self.command, cwd=path, timeout=timeout,
                                  stdout=PIPE, stderr=STDOUT, input='')
        except TimeoutExpired:
            raise BrokenSubmissionError('timeout of {} seconds expired'
                                        .format(self.timeout))

        if process.stdout is None:
            log = '(no output)'
        else:
            log = process.stdout.decode()

        if process.returncode:
            score = Fraction(0)
            log += '\n\nprocess exited with exit code {} != 0' \
                   .format(process.returncode)
        else:
            score = Fraction(1)

        return PartGrade(score=score, log=log)


class MultiCommandGrader(GraderInterface):
    """
    Run a bunch of commands, testing the exit code of each
    """

    DEFAULT_TIMEOUT = 30

    def __init__(self, timeout=None, extra_setup_commands=None):
        if timeout is None:
            self.timeout = self.DEFAULT_TIMEOUT
        else:
            self.timeout = timeout

        if extra_setup_commands is None:
            self.extra_setup_commands = []
        else:
            self.extra_setup_commands = extra_setup_commands

    def list_extra_setup_commands(self):
        return self.extra_setup_commands

    def part_from_config_dict(self, config_dict):
        return Command.from_config_dict(config_dict)

    def grade(self, submission, path, parts):
        return [part.grade(path, self.timeout) for part in parts]
