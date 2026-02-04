import threading
from multiprocessing import cpu_count
from abc import ABCMeta, abstractmethod

from . import GraderInterface
from ..utils import queue


"""
An implementation of GraderInterface which runs tests in separate
threads. In theory, speeds up grading by two times the number of
CPUs.

Actual graders can subclass this and implement grade_part() to become
threaded!
"""


class ThreadedGrader(GraderInterface):
    __metaclass__ = ABCMeta

    """
    A base class for graders to run parts in separate threads to speed
    up grading. Subclasses must implement grade_part().
    """

    def __init__(self, num_threads=None):
        if num_threads is None:
            try:
                cpus = cpu_count()
            except NotImplementedError:
                cpus = 1

            self.num_threads = 2 * cpus
        else:
            self.num_threads = num_threads

    @abstractmethod
    def grade_part(self, part, path, submission):
        """
        Grade a Part instance part, where the temporary grading
        directory is `path' and the Submission instance passed to
        grade() is `submission'.

        Must return a PartGrade instance.
        """
        pass

    def run_thread(self, path, submission, part_queue, grades):
        """
        One grading thread. Dequeues parts from part_queue until
        part_queue is empty and exits.
        """

        while True:
            try:
                part_index, part = part_queue.get(block=False)
            except queue.Empty:
                return

            try:
                grade = self.grade_part(part, path, submission)
            except Exception as err:
                grades[part_index] = err
                return

            grades[part_index] = grade

    def grade(self, submission, path, parts):
        """Spin off the configured number of grading threads and grade."""

        grades = [None] * len(parts)
        threads = []
        part_queue = queue.Queue()

        for index_part in enumerate(parts):
            part_queue.put(index_part)

        for _ in range(self.num_threads):
            args = (path, submission, part_queue, grades)
            thread = threading.Thread(target=self.run_thread, args=args)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        # Look for exceptions
        for grade in grades:
            if isinstance(grade, Exception):
                raise grade

        return grades
