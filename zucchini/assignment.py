import os
import shutil
import tempfile
from fractions import Fraction
from collections import namedtuple

import click
import yaml

from .submission import BrokenSubmissionError
from .grades import AssignmentComponentGrade, CalculatedGrade, \
                    CalculatedPenalty
from .graders import AVAILABLE_GRADERS
from .penalizers import AVAILABLE_PENALIZERS
from .constants import ASSIGNMENT_CONFIG_FILE, ASSIGNMENT_FILES_DIRECTORY
from .utils import ConfigDictMixin, copy_globs, sanitize_path


class ComponentPart(namedtuple('ComponentPart',
                               ['weight', 'part', 'partial_credit'])):
    def calculate_grade(self, component_points, total_part_weight, part_grade):
        points = component_points * Fraction(self.weight, total_part_weight)
        return part_grade.calculate_grade(points,
                                          self.part,
                                          self.partial_credit)


class AssignmentComponent(ConfigDictMixin):
    def __init__(self, assignment, name, backend, weight, parts, files=None,
                 optional_files=None, grading_files=None,
                 backend_options=None):
        self.assignment = assignment
        self.name = name
        self.backend = backend

        # Get the backend class
        if self.backend not in AVAILABLE_GRADERS:
            raise ValueError("Invalid grading backend: %s" % backend)

        backend_class = AVAILABLE_GRADERS[self.backend]

        self.weight = weight
        if type(self.weight) != int:
            raise ValueError("Component weights need to be integers.")

        self.files = files
        if self.files is not None:
            if not isinstance(self.files, list):
                raise ValueError('List of files must be a list')
            else:
                self.files = [sanitize_path(file_) for file_ in self.files]

        self.optional_files = optional_files
        if self.optional_files is not None:
            if not isinstance(self.optional_files, list):
                raise ValueError('List of optional files must be a list')
            else:
                self.optional_files = [sanitize_path(file_)
                                       for file_ in self.optional_files]

        # Check that there are no files marked as both optional and
        # required
        if None not in (self.files, self.optional_files):
            common = set(self.files).intersection(self.optional_files)
            if common:
                raise ValueError(
                    "file `{}' cannot be both an optional and required file!"
                    .format(next(iter(common))))

        # TODO: Confirm that all of the files in the grading list exist
        self.grading_files = grading_files
        if self.grading_files is not None:
            if not isinstance(self.grading_files, list):
                raise ValueError('List of grading files must be a list')
            else:
                self.grading_files = [sanitize_path(file_)
                                      for file_ in self.grading_files]

        # We then initialize the grader
        self.grader = backend_class.from_config_dict(backend_options or {})
        self.parts = []
        self.total_part_weight = 0

        for part_dict in parts:
            if 'weight' not in part_dict:
                raise ValueError('every part needs a weight!')
            else:
                weight = part_dict['weight']
                del part_dict['weight']

            partial_credit = True
            if 'partial-credit' in part_dict:
                partial_credit = part_dict['partial-credit']
                del part_dict['partial-credit']

            part = self.grader.part_from_config_dict(part_dict)
            self.parts.append(ComponentPart(weight=weight,
                                            part=part,
                                            partial_credit=partial_credit))
            self.total_part_weight += weight

    def is_interactive(self):
        """
        Return True if and only if this component will produce
        command-line prompts.
        """
        return self.grader.is_interactive()

    def list_prerequisites(self):
        """
        Return a list of Ubuntu 16.04 packages required to run this
        grader.
        """
        return self.grader.list_prerequisites()

    def list_extra_setup_commands(self):
        """
        This function should return a list of extra one-time commands to
        run at Docker image creation time. This is Ubuntu.
        """
        return self.grader.list_extra_setup_commands()

    def needs_display(self):
        """
        Return True if and only if this grader expects a graphical
        environment, like $DISPLAY on GNU/Linux.
        """
        return self.grader.needs_display()

    def grade_submission(self, submission):
        grading_directory = tempfile.mkdtemp(prefix='zucchini-component-')

        try:
            # Copy the submission first and the grading later so that if a file
            # exists in both, the grading copy overwrites the submission copy
            if self.optional_files:
                submission.copy_files(self.optional_files, grading_directory,
                                      allow_fail=True)
            if self.files:
                submission.copy_files(self.files, grading_directory)
            if self.grading_files:
                self.assignment.copy_files(self.grading_files,
                                           grading_directory)
            # self.parts is a list of (weight, Part) tuples, but we only
            # wanna pass Part instances to the grader
            parts = [part.part for part in self.parts]
            part_grades = self.grader.grade(submission, grading_directory,
                                            parts)
        except BrokenSubmissionError as err:
            return AssignmentComponentGrade(error=str(err),
                                            error_verbose=err.verbose)
        finally:
            shutil.rmtree(grading_directory)

        return AssignmentComponentGrade(part_grades)

    def calculate_grade(self, total_weight, component_grade):
        points = Fraction(self.weight, total_weight)
        return component_grade.calculate_grade(points, self.name,
                                               self.total_part_weight,
                                               self.parts)


class AssignmentPenalty(ConfigDictMixin):
    """Penalize students for late submissions etc."""

    def __init__(self, assignment, name, backend, backend_options=None):
        self.assignment = assignment
        self.name = name

        # Get the backend class
        if backend not in AVAILABLE_PENALIZERS:
            raise ValueError("Invalid penalizer backend: %s" % backend)

        backend_class = AVAILABLE_PENALIZERS[backend]

        # We then initialize the grader
        self.penalizer = backend_class.from_config_dict(backend_options or {})

    def calculate(self, submission, grade):
        """Return `grade' as a Fraction adjusted for the given submission"""

        adjusted_grade = self.penalizer.adjust_grade(submission, grade)
        return CalculatedPenalty(name=self.name,
                                 points_delta=adjusted_grade - grade)


# This class contains the Assignment configuration for the local file
class Assignment(object):
    def __init__(self, root):
        self.root = root

        config_file_path = os.path.join(self.root, ASSIGNMENT_CONFIG_FILE)

        if not os.path.exists(config_file_path):
            raise ValueError("This directory is not a valid Zucchini "
                             "assignment: the Zucchini config is missing.")

        with click.open_file(config_file_path, 'r') as config_file:
            config = yaml.safe_load(config_file)

        if config is None:
            raise ValueError("The assignment configuration file could not be "
                             "parsed.")

        try:
            # Get the assignment's name, author
            self.name = config['name']
            self.author = config['author']
        except KeyError as e:
            raise ValueError("Missing field in assignment config: %s" %
                             e.args[0])

        # TODO: Don't hardcode Canvas logic in here. Need to make something
        #       like "Modules" for handling these things.
        if 'canvas' in config:
            try:
                self.canvas_course_id = int(config['canvas']['course-id'])
                self.canvas_assignment_id = \
                    int(config['canvas']['assignment-id'])
            except KeyError as err:
                raise ValueError('canvas section in assignment config is '
                                 'missing key: {}'.format(err.args[0]))
            except ValueError as err:
                raise ValueError('canvas id is not an integer: {}'
                                 .format(str(err)))
        else:
            self.canvas_course_id = None
            self.canvas_assignment_id = None

        self.components = []

        # Now load the components (this is the fun part!)
        for component_config in config['components']:
            component = AssignmentComponent.from_config_dict(component_config,
                                                             assignment=self)
            self.components.append(component)

        if len({component.name for component in self.components}) \
                != len(self.components):
            raise ValueError('Duplicate component names')

        self.total_weight = sum(c.weight for c in self.components)
        self.interactive = any(c.is_interactive() for c in self.components)
        self.noninteractive = any(not c.is_interactive()
                                  for c in self.components)
        self._needs_display = any(c.needs_display() for c in self.components)

        self.prerequisites = set()
        for component in self.components:
            self.prerequisites.update(component.list_prerequisites())

        self.extra_setup_commands = []
        backend_types_seen = set()
        for component in self.components:
            if component.backend not in backend_types_seen:
                backend_types_seen.add(component.backend)
                self.extra_setup_commands += \
                    component.list_extra_setup_commands()

        self.penalties = []

        for penalty_config in config.get('penalties', ()):
            penalty = AssignmentPenalty.from_config_dict(penalty_config,
                                                         assignment=self)
            self.penalties.append(penalty)

        # TODO: Handle assignments with no components or with 0 total weight

    def list_prerequisites(self):
        """
        Return a list of Ubuntu 16.04 packages needed by this assignment.
        """
        return list(self.prerequisites)

    def list_extra_setup_commands(self):
        """
        Return a list of Ubuntu commands to run at setup time.
        """
        return self.extra_setup_commands

    def has_interactive(self):
        """
        Return True if and only if grading this assignment will produce
        command-line prompts.
        """
        return self.interactive

    def has_noninteractive(self):
        """
        Return True if and only if grading this assignment contains at
        least one noninteractive grader.
        """
        return self.noninteractive

    def needs_display(self):
        """
        Return True if and only if at least one component expects a
        graphical environment, like $DISPLAY on GNU/Linux.
        """
        return self._needs_display

    def copy_files(self, files, path):  # (List[str], str) -> None
        """Copy the grader files in the files list to the new path"""

        grading_files_dir = os.path.join(self.root, ASSIGNMENT_FILES_DIRECTORY)
        # XXX Replace FileNotFoundError raised with a better exception
        copy_globs(files, grading_files_dir, path)

    def grade_submission(self, submission, interactive=None):
        """
        Grade each assignment component of submission, returning an
        AssignmentComponentGrade for each component.
        If interactive is None (the default), grade all components; if
        True, grade only interactive components, and if False, grade
        only noninteractive components.
        """

        # The grading data for each part (individual test) of each
        # component (test suite) of this assignment
        grades = [component.grade_submission(submission)
                  if interactive is None
                  or interactive == component.is_interactive() else None
                  for component in self.components]
        return grades
        # TODO: We probably want to log, too

    def calculate_grade(self, submission, component_grades):
        """
        Calculate the final grade for a submission given the list of
        AssignmentComponentGrades for the submission.
        """

        # First, calculate raw grade
        grade = CalculatedGrade(name=self.name, grade=Fraction(1),
                                raw_grade=Fraction(0), penalties=[],
                                components=[])

        for component, component_grade in zip(self.components,
                                              component_grades):
            calc_component_grade = component.calculate_grade(self.total_weight,
                                                             component_grade)
            grade.components.append(calc_component_grade)
            grade.grade += calc_component_grade.points_delta

        # Store grade pre-penalties
        grade.raw_grade = grade.grade

        # Now deduct for penalties
        for penalty in self.penalties:
            calc_penalty = penalty.calculate(submission, grade.grade)
            grade.penalties.append(calc_penalty)
            grade.grade += calc_penalty.points_delta

        return grade
