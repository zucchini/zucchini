from .exceptions import InvalidGraderConfigError
from .grader_interface import GraderInterface, Part
from .threaded_grader import ThreadedGrader
from .prompt_grader import PromptGrader
from .open_file_grader import OpenFileGrader
from .command_grader import CommandGrader
from .libcheck_grader import LibcheckGrader
from .junit_json_grader import JUnitJSONGrader
from .junit_xml_grader import JUnitXMLGrader
from .bitwise_json_grader import BitwiseJSONGrader
from .circuitsim_grader import CircuitSimGrader
from .pylc3_grader import PyLC3Grader
from .multi_command_grader import MultiCommandGrader
from .python_module_grader import PythonModuleGrader
from .lc3tools_grader import LC3ToolsGrader
from .lc3tools_legacy_grader import LC3ToolsLegacyGrader
from .ensemble_grader import EnsembleGrader
from .criterion_grader import CriterionGrader

__all__ = ['InvalidGraderConfigError', 'GraderInterface', 'Part',
           'ThreadedGrader', 'PromptGrader', 'OpenFileGrader', 'CommandGrader',
           'LC3ToolsGrader', 'LC3ToolsLegacyGrader', 'LibcheckGrader',
           'JUnitJSONGrader', 'JUnitXMLGrader', 'BitwiseJSONGrader',
           'CircuitSimGrader', 'PyLC3Grader', 'MultiCommandGrader',
           'PythonModuleGrader', 'EnsembleGrader', 'CriterionGrader']

_GRADERS = (
    PromptGrader,
    OpenFileGrader,
    CommandGrader,
    LC3ToolsGrader,
    LC3ToolsLegacyGrader,
    LibcheckGrader,
    JUnitJSONGrader,
    JUnitXMLGrader,
    BitwiseJSONGrader,
    CircuitSimGrader,
    PyLC3Grader,
    MultiCommandGrader,
    PythonModuleGrader,
	EnsembleGrader,
	CriterionGrader
)
AVAILABLE_GRADERS = {cls.__name__: cls for cls in _GRADERS}
