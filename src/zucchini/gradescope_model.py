import datetime as dt

from fractions import Fraction
from typing import Annotated
from typing_extensions import override
from pydantic import BaseModel, Field

from .assignment import AssignmentMetadata, IntoMetadata


class GradescopeUserAssignment(BaseModel):
    release_date: dt.datetime
    """Release date of the assignment for the user."""
    due_date: dt.datetime
    """Due date of the assignment for the user."""
    late_due_date: dt.datetime
    """Late due date of the assignment for the user."""

class GradescopeUser(BaseModel):
    user_id: Annotated[int, Field(alias="id")]
    """
    ID of author.

    This ID is used exclusively by Gradescope.
    """

    email: str
    """Email of author."""
    name: str
    """Name of author."""
    sid: int
    """
    Student ID.

    This ID is used throughout multiple systems,
    including those outside Gradescope.
    """
    assignment: GradescopeUserAssignment
    """Assignment metadata for the user."""
    sections: list[str]
    """Sections the author are a part of."""

class GradescopeCurrentAssignmentOutlineItem(BaseModel):
    outline_id: Annotated[int, Field(alias="id")]
    weight: Fraction
    # There are other fields, but I don't think it's worth serializing these

class GradescopeCurrentAssignment(BaseModel):
    assignment_id: Annotated[int, Field(alias="id")]
    """
    ID of the assignment.
    """

    title: str
    """Title of the assignment."""

    release_date: dt.datetime
    """Default release date of the assignment."""
    due_date: dt.datetime
    """Default due date of the assignment."""
    late_due_date: dt.datetime
    """Default late due date of the assignment."""
    total_points: Fraction
    """Total points for the assignment."""
    course_id: int
    """Course ID (used exclusively by Gradescope)."""
    group_submission: bool
    """Whether this assignment is a group submission."""
    group_size: int | None
    """Group size of assignment (None if `group_submission` is False)"""
    outline: list[GradescopeCurrentAssignmentOutlineItem]
    """Outline of tasks in assignment."""

class GradescopePreviousSubmission(BaseModel):
    submission_id: Annotated[int, Field(alias="id")]
    """ID of submission."""

    submission_time: dt.datetime
    """Datetime when the submission was created."""

    score: Fraction
    """Score received for submission."""

    autograder_error: bool
    """Whether the autograder ran correctly."""

    # results: list[...]
    # Don't want to implement this

class GradescopeMetadata(BaseModel, IntoMetadata):
    submission_id: Annotated[int, Field(alias="id")]
    """ID of submission."""

    users: list[GradescopeUser]
    """List of authors of the submission."""
    
    created_at: dt.datetime
    """Datetime when the submission was created."""

    # assignment_id: str | None
    # No idea what this is

    assignment: GradescopeCurrentAssignment
    """Data for current assignment"""

    previous_submissions: list[GradescopePreviousSubmission]
    """Previous submissions."""

    def due_date(self):
        """Due date for the assignment (based on the users' due dates)."""
        return max(u.assignment.due_date for u in self.users)
    
    @override
    def as_metadata(self, tester_dir):
        return AssignmentMetadata(
            total_points=self.assignment.outline[0].weight,
            tester_dir=tester_dir,
            due_date=self.due_date(),
        )