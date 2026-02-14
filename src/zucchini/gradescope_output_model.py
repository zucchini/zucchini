from typing import Any, Literal
from pydantic import BaseModel, TypeAdapter

from zucchini.exceptions import ZucchiniError
from zucchini.grades import AssignmentGrade, ComponentGrade

OutputVisibility = Literal["hidden", "after_due_date", "after_published", "visible"]
"""
Visibility of an assignment grade, test, or output.

<https://gradescope-autograders.readthedocs.io/en/latest/specs/#controlling-test-case-visibility>
"""
TestStatus = Literal["passed", "failed"]
"""
Status of a given test case.

<https://gradescope-autograders.readthedocs.io/en/latest/specs/#test-case-status>
"""
OutputFormat = Literal["text", "html", "simple_format", "md", "ansi"]
"""
Format of text.

<https://gradescope-autograders.readthedocs.io/en/latest/specs/#output-string-formatting>
"""

def _get_status(passed: bool) -> TestStatus:
    """
    Override how Gradescope determines status.
    
    If a student gets 0% of 0 points, it is interpreted as a pass
    (even if the test failed).

    To circumvent this, we instead use the grade's `passed` variables,
    which keep track of when the tests succeed
    (as opposed to keeping track of weighted score).
    """
    return "passed" if passed else "failed"
def _error_output(error: ZucchiniError):
    base = f"{error}\n{error.verbose or ''}".strip()
    if error.is_it_autograders_fault:
        ANSI_RED ="\x1b[31m"
        ANSI_RESET = "\x1b[0m"
        base += (
            f"\n\n{ANSI_RED}This appears to be an autograder bug. "
            f"Please report this as an autograder error to your instructors.{ANSI_RESET}"
        )
    return base

class GradescopeTestOutput(BaseModel):
    score: float | None = None
    max_score: float | None = None
    status: TestStatus | None = None
    name: str | None = None
    name_format: OutputFormat | None = None
    number: str | None = None
    output: str | None = None
    output_format: OutputFormat | None = None
    tags: list[str] | None = None
    visibility: OutputVisibility | None = None
    extra_data: dict[Any, Any] | None = None

class GradescopeOutput(BaseModel):
    """
    Gradescope autograder output, as specified in:
    <https://gradescope-autograders.readthedocs.io/en/latest/specs/#output-format>
    """

    score: float | None = None
    execution_time: int | None = None
    output: str | None = None
    output_format: OutputFormat | None = None
    test_output_format: OutputFormat | None = None
    test_name_format: OutputFormat | None = None
    visibility: OutputVisibility | None = None
    stdout_visibility: OutputVisibility | None = None
    extra_data: dict[Any, Any] | None = None
    tests: list[GradescopeTestOutput] | None = None

    @classmethod
    def from_grade(cls, grade: AssignmentGrade):
        tests: list[GradescopeTestOutput] = []
        
        # Penalties:
        for penalty in grade.penalties:
            if penalty.points_deducted != 0:
                score = float(-max(0, penalty.points_deducted))
                tests.append(GradescopeTestOutput(
                    name=penalty.name,
                    score=score,
                    max_score=0,
                    status="failed" if penalty.points_deducted > 0 else "passed",
                ))
        
        # Actual test results
        for component in grade.components:
            if component.error:
                # Broken error
                score = float(component.points_received() * grade.max_points)
                max_score = float(component.norm_weight * grade.max_points)

                tests.append(GradescopeTestOutput(
                    name=component.description,
                    score=score,
                    max_score=max_score,
                    status=_get_status(component.passed()),
                    output=_error_output(component.error),
                ))
            else:
                # Tests
                for part in (component.parts or []):
                    score = float(part.points_received() * component.norm_weight * grade.max_points)
                    max_score = float(part.norm_weight * component.norm_weight * grade.max_points)

                    deductions = ""
                    if part.inner.deductions:
                        deductions = f"Deductions: {', '.join(part.inner.deductions)}\n\n"
                    output = deductions + (part.inner.log or "")

                    tests.append(GradescopeTestOutput(
                        name=f"{component.description}: {part.description}",
                        score=score,
                        max_score=max_score,
                        status=_get_status(part.passed()),
                        output=output
                    ))

        extra_data = {
            "component_grades": TypeAdapter(list[ComponentGrade]).dump_json(grade.components)
        }
        return cls(
            score=float(grade.final_grade()),
            tests=tests,
            extra_data=extra_data,
            output_format="ansi",
            test_output_format="ansi",
        )