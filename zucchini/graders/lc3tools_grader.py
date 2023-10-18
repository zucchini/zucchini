import os
import tempfile
import sys
from fractions import Fraction

from ..submission import BrokenSubmissionError
from ..utils import run_process, PIPE, STDOUT, TimeoutExpired
from ..grades import PartGrade
from . import ThreadedGrader, Part


class LC3ToolsTest(Part):
    __slots__ = ('name')

    def __init__(self, name):
        self.name = name

    def description(self):
        return self.name
    
    @staticmethod
    def format_cmd(cmd, **kwargs):
        return [arg.format(**kwargs) for arg in cmd]

    def grade(self, path, grader):
        grade = PartGrade(Fraction(1), log='')

        logfile_fp, logfile_path = tempfile.mkstemp(prefix='log-', dir=path)
        # Don't leak fds
        os.close(logfile_fp)
        logfile_basename = os.path.basename(logfile_path)

        run_cmd = self.format_cmd(grader.cmdline, testcase=self.name,
                                  logfile=logfile_basename)
        
        process = run_process(run_cmd,
                              env={'CK_DEFAULT_TIMEOUT':
                                   str(grader.timeout)},
                              cwd=path, stdout=PIPE, stderr=STDOUT)

        if process.returncode != 0:
            return self.test_error_grade('tester exited with {} != 0:\n{}'
                                         .format(process.returncode,
                                                 process.stdout.decode()
                                                 if process.stdout is not None
                                                 else '(no output)'))
        
        logfile_contents = process.stdout.decode()
        grade.log += "".join(logfile_contents.strip().splitlines(keepends=True)[:-1])
        summary = logfile_contents.splitlines()[-1]
        score = summary.replace("/", " ").split()[3:5]
        grade.score *= Fraction(int(score[0]), int(score[1]))

        return grade


class LC3ToolsGrader(ThreadedGrader):
    """
    Run a LC3Tools grader and collect the results.
    """

    DEFAULT_TIMEOUT = 30

    def __init__(self, test_file, asm_file, timeout=None, num_threads=None):

        super(LC3ToolsGrader, self).__init__(num_threads)
        self.test_file = test_file
        self.asm_file = asm_file

        self.cmdline = ["./" + self.test_file, self.asm_file, '--test_filter={testcase}',
                        "--tester-verbose"]

        self.timeout = self.DEFAULT_TIMEOUT \
            if timeout is None else timeout

    def list_prerequisites(self):
        return []

    def part_from_config_dict(self, config_dict):
        return LC3ToolsTest.from_config_dict(config_dict)
    
    def grade_part(self, part, path, submission):
        return part.grade(path, self)

    def grade(self, submission, path, parts):

        return super(LC3ToolsGrader, self).grade(submission, path, parts)