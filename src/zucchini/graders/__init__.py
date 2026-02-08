from .exceptions import InvalidGraderConfigError
from .grader_interface import GraderInterface, Part
from .threaded_grader import ThreadedGrader
from .bitwise_json_grader import BitwiseJSONGrader
from .circuitsim_grader import CircuitSimGrader
from .multi_command_grader import MultiCommandGrader
from .ensemble_grader import EnsembleGrader
from .criterion_grader import CriterionGrader

__all__ = ['InvalidGraderConfigError', 'GraderInterface', 'Part',
           'ThreadedGrader', 'BitwiseJSONGrader', 'CircuitSimGrader',
           'MultiCommandGrader', 'EnsembleGrader', 'CriterionGrader']

_GRADERS = (
    ThreadedGrader,
    BitwiseJSONGrader,
    CircuitSimGrader,
    MultiCommandGrader,
	EnsembleGrader,
	CriterionGrader
)
AVAILABLE_GRADERS = {cls.__name__: cls for cls in _GRADERS}
