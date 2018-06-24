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

__all__ = ['InvalidGraderConfigError', 'GraderInterface', 'Part',
           'ThreadedGrader', 'PromptGrader', 'OpenFileGrader', 'CommandGrader',
           'LibcheckGrader', 'JUnitJSONGrader', 'JUnitXMLGrader',
           'BitwiseJSONGrader', 'CircuitSimGrader']

_GRADERS = (
    PromptGrader,
    OpenFileGrader,
    CommandGrader,
    LibcheckGrader,
    JUnitJSONGrader,
    JUnitXMLGrader,
    BitwiseJSONGrader,
    CircuitSimGrader,
)
AVAILABLE_GRADERS = {cls.__name__: cls for cls in _GRADERS}
