"""
Utilities for local autograding.
"""

from zucchini.grades import AssignmentGrade

class LocalAutograderOutput:
    """
    Take a Grade object and convert that to an output string that will be
    printed into the terminal
    """

    @classmethod
    def from_grade(cls, grade: AssignmentGrade):
        output = []
        any_errors = False
        for component in grade.components:
            if component.error:
                any_errors = True
                output.append(f"ERROR: {component.description:45} {component.error:15}")
                output.append(f"Details: {component.error.verbose:45}")
            else:
                for part in (component.parts or []):
                    points_got = part.points_received() * component.norm_weight * grade.max_points
                    points_max = part.norm_weight * component.norm_weight * grade.max_points
                    points = f'{float(points_got):.2f}/{float(points_max):.2f}'
                    if part.passed():
                        output.append(f"TEST: {part.description:45} {'PASSED':15} ({points})")
                    else:
                        output.append(f"TEST: {part.description:45} {'FAILED':15} ({points})")
                        output.append(part.inner.log)
        score = f'Total score: {float(100 * grade.final_score):.2f}%'
        output.append(score)
        if any_errors:
            output.append('Some errors occurred; the score above may not be'
                          ' your final grade')
        return '\n\n'.join(output)
