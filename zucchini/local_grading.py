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
