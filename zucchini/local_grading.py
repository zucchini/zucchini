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
                for part in component.parts:
                    if part.points_got < part.points_possible:
                        output.append("TEST: %-45s %-15s" %
                                      (part.name, "FAILED"))
                        output.append(part.log)
                    else:
                        output.append("TEST: %-45s %-15s" %
                                      (part.name, "PASSED"))
        return '\n\n'.join(output)
