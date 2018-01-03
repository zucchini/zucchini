from fractions import Fraction

from .utils import ConfigDictMixin

"""Store grades for components and parts."""


class AssignmentComponentGrade(ConfigDictMixin):
    """Hold the score for an assignment component."""

    def __init__(self, part_grades=None, error=None, error_verbose=None):
        self.part_grades = part_grades
        self.error = error
        self.error_verbose = error_verbose

        if (self.part_grades is None) == (self.error is None):
            raise ValueError('need to specify either part-grades or error in '
                             'an AssignmentComponentGrade, but not both')

    def __repr__(self):
        return '<AssignmentComponentGrade part_grades={}>' \
               .format(self.part_grades)

    @classmethod
    def from_config_dict(cls, dict_):
        grade = super(AssignmentComponentGrade, cls).from_config_dict(dict_)
        if grade.part_grades:
            grade.part_grades = [PartGrade.from_config_dict(g)
                                 for g in grade.part_grades]
        return grade

    def to_config_dict(self, *args):
        dict_ = super(AssignmentComponentGrade, self).to_config_dict(*args)
        if dict_.get('part-grades', None):
            dict_['part-grades'] = [g.to_config_dict()
                                    for g in dict_['part-grades']]
        return dict_

    def is_broken(self):
        """
        Return True if and only if this submission was 'broken'; that
        is, processing it produced an unrecoverable error such as a
        missing file or noncompiling code.
        """
        return self.error is not None

    def calculate_grade(self, component_parts):
        # type: (List[ComponentPart]) -> fractions.Fraction
        """
        Using the list of ComponentPart instances provided (which
        contain the weight of components) and the part grades held in
        this instance, calculate the percentage of this component
        earned.
        """
        if self.is_broken():
            return Fraction(0)
        else:
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

    __slots__ = ('score', 'deductions', 'log')

    def __init__(self, score, deductions=None, log=None):
        self.score = Fraction(score)
        self.deductions = deductions
        self.log = log

    def __repr__(self):
        return '<PartGrade score={}, deductions={}, log={}>' \
               .format(self.score, self.deductions, self.log)

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
