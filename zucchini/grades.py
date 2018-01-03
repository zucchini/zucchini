from fractions import Fraction

from .utils import ConfigDictMixin

"""Store grades for components and parts."""


class AssignmentComponentGrade(ConfigDictMixin):
    """Hold the score for an assignment component."""

    def __init__(self, part_grades):
        self.part_grades = part_grades

    @classmethod
    def from_config_dict(cls, dict_):
        grade = super(AssignmentComponentGrade, cls).from_config_dict(dict_)
        grade.part_grades = [PartGrade.from_config_dict(g)
                             for g in grade.part_grades]
        return grade

    def to_config_dict(self, *args):
        dict_ = super(AssignmentComponentGrade, self).to_config_dict(*args)
        dict_['part-grades'] = [g.to_config_dict()
                                for g in dict_['part-grades']]
        return dict_

    def calculate_grade(self, component_parts):
        # type: (List[ComponentPart]) -> fractions.Fraction
        """
        Using the list of ComponentPart instances provided (which
        contain the weight of components) and the part grades held in
        this instance, calculate the percentage of this component
        earned.
        """
        total_possible = sum(part.weight for part in component_parts)
        total_earned = sum(grade.score * part.weight
                           for grade, part
                           in zip(self.part_grades, component_parts))
        return Fraction(total_earned, total_possible)


class PartGrade(ConfigDictMixin):
    """
    Hold the results of grading one part.

    score is the percentage passed as a Fraction instance, deductions is
    a list of deduction ids, and log is a string containing verbose logs
    for this part.
    """

    __slots__ = ('id', 'score', 'deductions', 'log')

    def __init__(self, score, deductions=None, log=None):
        self.score = Fraction(score)
        self.deductions = deductions
        self.log = log

    def to_config_dict(self, *exclude):
        result = super(PartGrade, self).to_config_dict(exclude)
        # Convert Fraction instance to a string
        result['score'] = str(result['score'])
        return result

    @classmethod
    def from_config_dict(cls, config_dict):
        part_grade = super(PartGrade, cls).from_config_dict(config_dict)
        # Convert string to Fraction instance
        part_grade.score = Fraction(part_grade.score)
        return part_grade
