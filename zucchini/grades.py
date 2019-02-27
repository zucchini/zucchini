from fractions import Fraction

from .utils import ConfigDictMixin, Record

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

    def calculate_grade(self, points, name, total_part_weight,
                        component_parts):
        """
        Using the list of ComponentPart instances provided (which
        contain the weight of components) and the part grades held in
        this instance, calculate the CalculatedComponentGrade tree for
        this grade.
        """

        grade = CalculatedComponentGrade(name=name,
                                         points_delta=Fraction(0),
                                         points_got=Fraction(0),
                                         points_possible=Fraction(0),
                                         grade=Fraction(1),
                                         error=None,
                                         error_verbose=None,
                                         parts=[])

        if self.is_broken():
            grade.points_got = Fraction(0)
            grade.error = self.error
            grade.error_verbose = self.error_verbose
        else:
            for part, part_grade in zip(component_parts, self.part_grades):
                calc_part_grade = part.calculate_grade(
                    points, total_part_weight, part_grade)
                grade.parts.append(calc_part_grade)
                grade.points_got += calc_part_grade.points_got

        grade.points_possible = points
        grade.points_delta = grade.points_got - grade.points_possible
        grade.grade = Fraction(grade.points_got, grade.points_possible)

        return grade


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

    def calculate_grade(self, points, part, partial_credit):
        points_got = self.score * points
        if not partial_credit and points_got < points:
            points_got = Fraction(0)

        return CalculatedPartGrade(name=part.description(),
                                   points_delta=points_got - points,
                                   points_got=points_got,
                                   points_possible=points,
                                   grade=self.score,
                                   deductions=self.deductions,
                                   log=self.log)


class CalculatedGrade(Record):
    """
    Hold the results of grading an assignment. Any numbers are a
    Fraction instance representing actual over possible.
    """
    __slots__ = ['name', 'grade', 'raw_grade', 'penalties', 'components']


class CalculatedPenalty(Record):
    """
    Hold the result of applying (or not applying) a penalty. Any numbers
    are a Fraction instance representing actual over possible.
    """
    __slots__ = ['name', 'points_delta']


class CalculatedComponentGrade(Record):
    """
    Hold the result of grading an assignment component. If error is not
    None, it is an error message string explaining why the submission is
    broken. Any numbers are a Fraction instance representing actual over
    possible.
    """
    __slots__ = ['name', 'points_delta', 'points_got', 'points_possible',
                 'grade', 'error', 'error_verbose', 'parts']


class CalculatedPartGrade(Record):
    """
    Hold the result of grading a single part (test) of an assignment
    component. Any numbers are a Fraction instance representing actual
    over possible.
    """
    __slots__ = ['name', 'points_delta', 'points_got', 'points_possible',
                 'grade', 'deductions', 'log']
