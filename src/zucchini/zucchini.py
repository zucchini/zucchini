# -*- coding: utf-8 -*-

"""This file contains the ZucchiniState class that provides context for the
grader. The context should include the grader's local configuration,
the Assignment object related to the assignment in the present directory if
one exists, and an instance of the FarmManager class."""

from .assignment import Assignment


class ZucchiniState(object):
    def __init__(self, assignment_directory):
        self.assignment_directory = assignment_directory
        self.submission_dir = None
        self._assignment = None

    def get_assignment(self):
        """
        Return an Assignment instance based on the configuration for this
        assignment.
        """

        if self._assignment is None:
            self._assignment = Assignment(self.assignment_directory)

        return self._assignment
