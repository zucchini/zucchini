from .exceptions import InvalidGraderConfigError
from .grader_interface import GraderInterface, Part
from .libcheck_grader import LibcheckGrader
from .junit_xml_grader import JUnitXMLGrader
from .bitwise_json_grader import BitwiseJSONGrader
from .circuitsim_grader import CircuitSimGrader
from .multi_command_grader import MultiCommandGrader
from .python_module_grader import PythonModuleGrader
from .ensemble_grader import EnsembleGrader
from .criterion_grader import CriterionGrader

__all__ = ['InvalidGraderConfigError', 'GraderInterface', 'Part',
           'LibcheckGrader','JUnitXMLGrader', 'BitwiseJSONGrader',
           'CircuitSimGrader', 'MultiCommandGrader', 'PythonModuleGrader',
           'EnsembleGrader', 'CriterionGrader']

_GRADERS = (
    LibcheckGrader,
    JUnitXMLGrader,
    BitwiseJSONGrader,
    CircuitSimGrader,
    MultiCommandGrader,
    PythonModuleGrader,
	EnsembleGrader,
	CriterionGrader
)
AVAILABLE_GRADERS = {cls.__name__: cls for cls in _GRADERS}
