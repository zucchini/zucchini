"""
Utilities for gradescope autograding.
"""

import json

from .utils import ConfigDictMixin, ConfigDictNoMangleMixin, \
                   datetime_from_string


class GradescopeMetadata(object):
    """
    Parse the metadata as described in:
    https://gradescope-autograders.readthedocs.io/en/latest/submission_metadata/
    """

    _ATTRS = {
        'id': int,
        'created_at': datetime_from_string,
        'assignment_id': int,
    }

    def __init__(self, json_dict):
        for attr, type_ in self._ATTRS.items():
            setattr(self, attr, type_(json_dict[attr]))

    @classmethod
    def from_json_path(cls, json_path):
        with open(json_path, 'r') as json_fp:
            return cls(json.load(json_fp))


class GradescopeAutograderTestOutput(ConfigDictNoMangleMixin, ConfigDictMixin):
    """
    Output of a single test in Gradescope JSON.
    """

    def __init__(self, name=None, score=None, max_score=None, output=None):
        self.score = float(score) if score is not None else None
        self.max_score = float(max_score) if max_score is not None else None
        self.output = output


class GradescopeAutograderOutput(ConfigDictNoMangleMixin, ConfigDictMixin):
    """
    Hold Gradescope Autograder output as described in
    https://gradescope-autograders.readthedocs.io/en/latest/specs/#output-format
    """

    def __init__(self, score=None, tests=None, extra_data=None):
        self.score = score
        self.tests = [GradescopeAutograderTestOutput.from_config_dict(test)
                      for test in tests] if tests is not None else None
        self.extra_data = extra_data

    def to_config_dict(self, *args):
        dict_ = super(GradescopeAutograderOutput, self).to_config_dict(*args)
        if dict_.get('tests', None):
            dict_['tests'] = [test.to_config_dict() for test in dict_['tests']]
        return dict_

    @classmethod
    def from_grade(cls, grade):
        """
        Convert a grading_manager.Grade to Gradescope JSON.
        """

        score = grade.score()
        tests = []
        # Store the component grades in the extra_data field
        extra_data = grade.serialized_component_grades()

        computed_grade = grade.computed_grade()

        # Add penalties
        for penalty in computed_grade.penalties:
            if penalty.points_delta != 0:
                test = GradescopeAutograderTestOutput(
                    name=penalty.name,
                    score=grade.to_float(penalty.points_delta))
                tests.append(test)

        # Add actual test results
        for component in computed_grade.components:
            for part in component.parts:
                if part.deductions:
                    deductions = 'Deductions: {}\n\n'.format(
                        ', '.join(part.deductions))
                else:
                    deductions = ''

                test = GradescopeAutograderTestOutput(
                    name='{}: {}'.format(component.name, part.name),
                    score=grade.to_float(part.points_got),
                    max_score=grade.to_float(part.points_possible),
                    output=deductions + part.log)
                tests.append(test)

        return cls(score=score, tests=tests, extra_data=extra_data)

    def to_json_stream(self, fp):
        json.dump(self.to_config_dict(), fp)
