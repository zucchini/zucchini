# import shlex
# from fractions import Fraction

# from ..submission import BrokenSubmissionError
# from ..utils import run_process, PIPE, STDOUT, TimeoutExpired
# from ..grades import PartGrade
# from . import GraderInterface, Part

"""
Grade a homework with the lc3tools autograding library
"""


## Commenting this out for the time being so I can figure out what exactly needs to be implemented and how
## I'd like to implement something similar to the command_grader where it just runs a single command
## The existing command grader seems to only check for exit code, but the stdout of the new autograder is a bit more robust.
## Output looks something like this:

# attempting to assemble tutorial_sol.asm into tutorial_sol.obj
# assembly successful
# ==========
# Test: Zero Test
#   Is Zero? => Pass (+10 pts)
# Test points earned: 10/10 (100%)
# ==========
# ==========
# Total points earned: 10/10 (100%)

## We should be able to reuse much of the command_grader but just need to add custom parsing.
## I think we should be able to check for "Pass" pretty easy and then return either 0 or 1.
## This would also mean that assigning points in the autograder would be redundant (as we'd just distribute weights thru zucchini)

## TOOK THIS FROM multi_command_grader:
# class LC3ToolsGrader(Part):
#     """Runs a test suite on an LC3 program"""

#     __slots__ = ('summary', 'command')

#     def __init__(self, summary, command):
#         self.summary = summary
#         self.command = shlex.split(command)

#     def description(self):
#         return self.summary

#     def grade(self, path, timeout):
#         try:
#             process = run_process(self.command, cwd=path, timeout=timeout,
#                                   stdout=PIPE, stderr=STDOUT, input='')
#         except TimeoutExpired:
#             raise BrokenSubmissionError('timeout of {} seconds expired'
#                                         .format(self.timeout))

#         if process.stdout is None:
#             log = '(no output)'
#         else:
#             log = process.stdout.decode()

#         grade = getGradeFromGraderOutput(log)

#         if process.returncode:
#             score = Fraction(0)
#             log += '\n\nprocess exited with exit code {} != 0' \
#                    .format(process.returncode)
#         else:
#             score = Fraction(1)

#         return PartGrade(score=score, log=log)


## TOOK THIS FROM THE LC3TOOLS REPO:
## Extract the raw grade from the grade report.
# def getGradeFromGraderOutput(grader_output):
#     lines = [x.rstrip() for x in grader_output.split('\n')]
#     if len(lines) < 2: return 0
#     if not 'successful' in lines[1]: return 0
#     return float(lines[-2].split(' ')[3].split('/')[0])
