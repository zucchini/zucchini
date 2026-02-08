from pathlib import Path
from abc import abstractmethod
from typing import Generic
from typing_extensions import override
import concurrent.futures

from ..grades import PartGrade
from ..submission import Submission


from ..graders.grader_interface import P
from . import GraderInterface


"""
An implementation of GraderInterface which runs tests in separate
threads. In theory, speeds up grading by two times the number of
CPUs.

Actual graders can subclass this and implement grade_part() to become
threaded!
"""

class ThreadedGrader(GraderInterface[P], Generic[P]):
    """
    A base class for graders to run parts in separate threads to speed
    up grading. Subclasses must implement grade_part().
    """
    num_threads: int | None = None

    @abstractmethod
    def grade_part(self, part: P, path: Path, submission: Submission) -> PartGrade:
        """
        Grade a Part instance part, where the temporary grading
        directory is `path' and the Submission instance passed to
        grade() is `submission'.

        Must return a PartGrade instance.
        """
        pass

    @override
    def grade(self, submission, path, parts) -> list[PartGrade]:
        """Spin off the configured number of grading threads and grade."""

        grades: list[PartGrade | None] = [None] * len(parts)

        try:
            pool = concurrent.futures.ThreadPoolExecutor(thread_name_prefix="zgrader")
            # Create all futures
            futures = {pool.submit(self.grade_part, part, path, submission): i for i, part in enumerate(parts)}
            for fut in concurrent.futures.as_completed(futures):
                if (exc := fut.exception()) is not None:
                    raise exc
                
                # When a future is completed, insert it into grades
                index = futures[fut]
                grades[index] = fut.result()
        finally:
            pool.shutdown(wait=True, cancel_futures=True)

        return grades # type: ignore
