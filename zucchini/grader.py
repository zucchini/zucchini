"""Zucchini grader logic"""

import os.path
import threading
import queue
from configparser import ConfigParser
from .backends.c import CBackend
from .backends.lc3 import LC3Backend
from .grading import StudentGrade, StudentGradeAborted

class Grader:
    """
    Execute lc3test for each configured test and calculate the final
    grade
    """

    def __init__(self, config_fp, submissions_dir, students=None,
                 exclude_students=None, skip_to=None):
        """Create a Grader by parsing config_fp and scanning submissions_dir"""

        self.parse_config(config_fp)
        self.submissions_dir = submissions_dir
        self.students = students if students is not None else \
                        self.find_students(submissions_dir)
        if exclude_students is not None:
            self.students = [student for student in self.students
                             if student not in exclude_students]
        if skip_to is not None:
            self.students = self.students[self.students.index(skip_to):]

        if not self.students:
            raise FileNotFoundError('no student submissions found')
        elif not os.path.isdir(submissions_dir):
            raise FileNotFoundError("could not find submissions dir `{}'"
                                    .format(submissions_dir))
        else:
            # Check for non-existent students here so we blow up at startup
            # instead of right in the middle of grading, which would be
            # annoying
            for student in self.students:
                path = os.path.join(self.submissions_dir, student)
                if not os.path.isdir(path):
                    raise FileNotFoundError("could not find student submission "
                                            "dir `{}'".format(path))

        # Attempt global backend setup
        self.backend.global_setup()

    def parse_config(self, config_fp):
        """Parse config in the file-like object config_fp"""

        self.config = ConfigParser()
        self.config.read_file(config_fp)

        # Detect backend
        if ('LC-3' in self.config) == ('C' in self.config):
            raise ValueError('You need to configure either the LC-3 or C '
                             'backend, but not both')
        else:
            self.backend = CBackend(**self.config['C']) if 'C' in self.config else \
                           LC3Backend(**self.config['LC-3'])

        self.description = self.config.get('META', 'description')
        self.signoff = self.config.get('META', 'signoff')
        self.tests = []
        for section in self.config.sections():
            if section in ('META', 'C', 'LC-3'):
                continue
            self.tests.extend(self.backend.new_tests(name=section, **self.config[section]))

        total_weights = sum(t.weight for t in self.tests)

        if total_weights == 0:
            raise ValueError('Test weights add up to 0 instead of 100. Did '
                             'you forget to add tests to the config file?')
        elif total_weights != 100:
            raise ValueError('Test weights do not add up to 100')

    @staticmethod
    def find_students(submissions_dir):
        """
        Scan submissions_dir for student submission directories created by
        SubmissionFix.py
        """

        return sorted(ent for ent in os.listdir(submissions_dir) if ',' in ent)

    def get_students(self):
        """Return list of student names"""

        return self.students

    def grade(self, student, skip_tests=None):
        """
        Grade student's work, returning a StudentGrade instance containing
        results
        """

        if skip_tests is None:
            skip_tests = []

        path = os.path.join(self.submissions_dir, student)

        # Default to the safe assumption, 1 CPU, if we can't count the
        # number of CPUs
        num_threads = 2 * (os.cpu_count() or 1)
        threads = []
        test_queue = queue.Queue()
        result_queue = queue.Queue()
        grade = StudentGrade(self.description, student, self.signoff)

        try:
            self.backend.student_setup(path)

            for test in self.tests:
                if test in skip_tests:
                    grade.add_test_grade(test.skip())
                else:
                    test_queue.put(test)

            for _ in range(num_threads):
                thread = threading.Thread(target=self.run_thread,
                                          args=(path, test_queue, result_queue))
                thread.start()
                threads.append(thread)

            for thread in threads:
                thread.join()

            while not result_queue.empty():
                result = result_queue.get(block=False)
                if isinstance(result, Exception):
                    raise result
                else:
                    grade.add_test_grade(result)

            # Write gradeLog.txt
            self.write_raw_gradelog(student, grade.gradelog())
        finally:
            self.backend.student_cleanup(path)

        return grade

    @staticmethod
    def run_thread(path, test_queue, result_queue):
        """
        Dequeue Tests from test_queue until test_queue is empty, running them
        at the path given and enqueue the results in result_queue.
        """

        while True:
            try:
                test = test_queue.get(block=False)
            except queue.Empty:
                return

            try:
                result = test.run(path)
            except Exception as err: # pylint: disable=broad-except
                result_queue.put(err)
                return
            else:
                result_queue.put(result)

    def setup_abort(self, student, setup_err):
        """
        Handle a SetupError by writing error details to the grader log and
        returning a fake StudentGrade instance giving them a zero.
        """

        self.write_raw_gradelog(student, setup_err.output or setup_err.message.encode())
        return StudentGradeAborted(self.description, student, self.signoff, setup_err.summary)

    def write_raw_gradelog(self, student, data):
        """
        Write the bytes given to the student's grader log. Useful for when
        compilation fails and you want to log the error, but you don't have any
        test results yet.
        """

        open(os.path.join(self.submissions_dir, student, 'gradeLog.txt'), 'wb').write(data)
