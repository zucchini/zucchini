"""Zucchini LC-3 (lc3test) Backend"""

import os
import re
import subprocess
from fractions import Fraction
from ..grading import Backend, Test, StudentTestGrade, TestError

class LC3Backend(Backend):
    """Run tests with Brandon's lc3test"""

    def __init__(self, warning_deduction_percent, runs=100):
        self.runs = int(runs)
        self.warning_deduction_percent = Fraction(int(warning_deduction_percent), 100)

    def new_tests(self, **kwargs):
        """
        Return an LC3Test instance configured to test the given .asm file
        against the .xml file given for this ini section
        """

        yield LC3Test(runs=self.runs,
                      warning_deduction_percent=self.warning_deduction_percent,
                      **kwargs)

class LC3Test(Test):
    """
    Associate a test xml file with the .asm file to test and a weight.
    """

    REGEX_RESULT_LINE = re.compile(r'^Run\s+(?P<run_number>\d+)\s+'
                                   r'Grade:\s+(?P<score>\d+)/(?P<max_score>\d+)\s+.*?'
                                   r'Warnings:\s+(?P<warnings>\d+)$')

    def __init__(self, name, description, weight, asmfile, warning_deduction_percent, runs):
        super().__init__(name, description, weight)
        self.xml_file = name
        self.asm_file = asmfile
        self.warning_deduction_percent = warning_deduction_percent
        self.runs = runs

        if not os.path.isfile(self.xml_file):
            raise FileNotFoundError("could not find xml file `{}'".format(self.xml_file))

    def __str__(self):
        return "test `{}' on `{}'".format(self.xml_file, self.asm_file)

    def run(self, directory):
        """Run this test, returning the weighted grade"""

        grade = StudentTestGrade(self.description, self.weight)

        try:
            asm_path = self.find_file(self.asm_file, directory)
        except FileNotFoundError as err:
            raise TestError(self, str(err))

        process = subprocess.run(['lc3test', self.xml_file, asm_path,
                                  '-runs={}'.format(self.runs)],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)

        if process.returncode != 0:
            raise TestError(self, 'lc3test returned {} != 0: {}'
                                  .format(process.returncode,
                                          process.stdout.decode().strip()))

        grade.add_output(process.stdout)

        # Skip the last line because it's the "post your whole output on
        # piazza" line, and then grab the line for each run
        result_lines = process.stdout.splitlines()[-1 - self.runs:-1]

        found_warnings = False
        percentages_min = None

        for i, result_line in enumerate(result_lines):
            match = self.REGEX_RESULT_LINE.match(result_line.decode())
            if not match:
                raise TestError(self, 'lc3test produced some weird output. what the h*ck?')
            if int(match.group('run_number')) != i+1:
                raise TestError(self, 'lc3test run result lines are off!')
            score = int(match.group('score'))
            max_score = int(match.group('max_score'))
            percent = Fraction(score, max_score)
            found_warnings = found_warnings or int(match.group('warnings')) > 0

            if percentages_min is None or percent < percentages_min:
                percentages_min = percent

        grade.set_percent_success(percentages_min)

        if found_warnings:
            grade.deduct('warnings', self.warning_deduction_percent)

        return grade
