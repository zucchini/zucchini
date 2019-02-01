"""Provide submission filtering logic."""


class FilterableSubmission(object):
    """Provide an abstract way of getting information about a submission"""

    def __init__(self, base_obj):
        raise NotImplementedError

    def student_name(self):
        raise NotImplementedError

    def is_broken(self):
        raise NotImplementedError


class FilterableMetaSubmission(FilterableSubmission):
    """Filters a Canvas API submission response"""

    __slots__ = ('submission')

    def __init__(self, submission):
        self.submission = submission

    def student_name(self):
        return self.submission.student_name

    def is_broken(self):
        return self.submission.is_broken()


class FilterableCanvasSubmission(FilterableSubmission):
    """Filters a Canvas API submission response"""

    __slots__ = ('canvas_submission')

    def __init__(self, canvas_submission):
        self.canvas_submission = canvas_submission

    def student_name(self):
        return self.canvas_submission.user.sortable_name


class FilterCondition(object):
    """
    Base class for a submission filter condition.

    At least one sufficient condition matching will cause a filter match
    provided all necessary conditions match. If the filter doesn't
    really make sense, not applicable will exclude it entirely.
    """
    __slots__ = ()

    SUFFICIENT, NECESSARY, NOT_APPLICABLE = range(3)

    def type(self):
        """
        Return whether this condition is sufficient or necessary.
        """
        pass

    def accepts(self, submission):
        """Return True if this submission matches the condition, """
        pass


class FilterBrokenCondition(object):
    """Filter for broken submissions"""
    __slots__ = ('is_broken')

    def __init__(self, is_broken):
        self.is_broken = is_broken

    def type(self):
        return FilterCondition.NECESSARY

    def accepts(self, submission):
        # XNOR (pronounced by Conte as "snore")
        return submission.is_broken() == self.is_broken


class FilterStudentCondition(object):
    """Filter by student name"""
    __slots__ = ('student_name')

    def __init__(self, student_name):
        self.student_name = student_name

    def type(self):
        return FilterCondition.SUFFICIENT

    def accepts(self, submission):
        return submission.student_name() == self.student_name


class FilterNotStudentCondition(object):
    """Exclude by student name"""
    __slots__ = ('student_name')

    def __init__(self, student_name):
        self.student_name = student_name

    def type(self):
        return FilterCondition.NECESSARY

    def accepts(self, submission):
        return submission.student_name() != self.student_name


class FilterBuilder(object):
    """
    Filter assignment submissions. Considers the logical OR of all
    conditions added. If no conditions are added, will match all
    submissions.
    """

    def __init__(self, filterable_class):
        self.filterable_class = filterable_class
        self.conditions = []

    @classmethod
    def new_canvas(cls):
        """Return a FilterBuilder ready to handle Canvas API responses"""
        return cls(FilterableCanvasSubmission)

    @classmethod
    def new_meta(cls):
        """Return a FilterBuilder ready to handle submission metadata"""
        return cls(FilterableMetaSubmission)

    def __call__(self, submission):
        # Convert this lower-level object into something we can pass to
        # the higher-level filters
        filterable = self.filterable_class(submission)

        necessary_met = True
        sufficient_met = False
        # Still want to accept a submission if we have no sufficient
        # conditions
        found_sufficient_condition = False
        for cond in self.conditions:
            try:
                result = cond.accepts(filterable)
            except NotImplementedError:
                # Some filters aren't implemented for some submission
                # types. For example, it doesn't make much sense for a
                # Canvas API submission to be 'broken'
                continue

            if cond.type() == FilterCondition.NECESSARY:
                necessary_met = necessary_met and result
            elif cond.type() == FilterCondition.SUFFICIENT:
                found_sufficient_condition = True
                sufficient_met = sufficient_met or result

        return necessary_met \
            and (not found_sufficient_condition or sufficient_met)

    def add_student_name(self, student_name):
        self.conditions.append(FilterStudentCondition(student_name))

    def add_not_student_name(self, student_name):
        self.conditions.append(FilterNotStudentCondition(student_name))

    def add_broken(self, is_broken):
        self.conditions.append(FilterBrokenCondition(is_broken))
