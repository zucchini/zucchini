"""
Utilities for local autograding.
"""

from zucchini.grades import AssignmentGrade2

class LocalAutograderOutput2:
    """
    Take a Grade object and convert that to an output string that will be
    printed into the terminal
    """

    @classmethod
    def from_grade(cls, grade: AssignmentGrade2):
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


class LocalAutograderOutput:
    """
    Take a Grade object and convert that to an output string that will be
    printed into the terminal
    """

    @classmethod
    def from_grade(cls, grade):
        computed_grade = grade.computed_grade()
        output = []
        total_got = 0.0
        total_max = 0.0
        any_errors = False
        for component in computed_grade.components:
            total_got += component.points_got
            total_max += component.points_possible
            if component.error:
                any_errors = True
                output.append("ERROR: %-45s %-15s" %
                              (component.name, component.error))
                output.append("Details: %-45s" % component.error_verbose)
            else:
                for part in component.parts:
                    points_got = grade.to_float(part.points_got)
                    points_max = grade.to_float(part.points_possible)
                    points = '{:.2f}/{:.2f}'.format(points_got, points_max)
                    if part.points_got < part.points_possible:
                        output.append("TEST: %-45s %-15s (%s)" %
                                      (part.name, "FAILED", points))
                        output.append(part.log)
                    else:
                        output.append("TEST: %-45s %-15s (%s)" %
                                      (part.name, "PASSED", points))
        score_percentage = 100.0 * total_got / total_max
        score = 'Total score: {:.2f}%'.format(score_percentage)
        output.append(score)
        if any_errors:
            output.append('Some errors occurred; the score above may not be'
                          ' your final grade')
        return '\n\n'.join(output)
