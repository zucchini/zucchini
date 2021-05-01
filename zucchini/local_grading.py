"""
Utilities for local autograding.
"""


class LocalAutograderOutput:
    """
    Take a Grade object and convert that to an output string that will be
    printed into the terminal
    """

    @classmethod
    def from_grade(cls, grade):
        computed_grade = grade.computed_grade()
        output = []
        for component in computed_grade.components:
            if component.error:
                output.append("ERROR: %-45s %-15s" %
                              (component.name, component.error))
                output.append("Details: %-45s" % component.error_verbose)
            else:
                total_got = 0.0
                total_max = 0.0
                for part in component.parts:
                    points_got = grade.to_float(part.points_got)
                    points_max = grade.to_float(part.points_possible)
                    total_got += points_got
                    total_max += points_max
                    points = '{:.2f}/{:.2f}'.format(points_got, points_max)
                    if part.points_got < part.points_possible:
                        output.append("TEST: %-45s %-15s (%s)" %
                                      (part.name, "FAILED", points))
                        output.append(part.log)
                    else:
                        output.append("TEST: %-45s %-15s (%s)" %
                                      (part.name, "PASSED", points))
                output.append('Final score: {:.2f}/{:.2f}'.format(
                    total_got, total_max))
        return '\n\n'.join(output)
