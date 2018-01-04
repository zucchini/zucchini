from .exceptions import InvalidGraderConfigError
from .grader_interface import GraderInterface, Part
from .prompt_grader import PromptGrader
from .open_file_grader import OpenFileGrader
from .libcheck_grader import LibcheckGrader

__all__ = ['InvalidGraderConfigError', 'GraderInterface', 'Part',
           'PromptGrader', 'OpenFileGrader', 'LibcheckGrader']

_GRADERS = (
    PromptGrader,
    OpenFileGrader,
    LibcheckGrader,
)
AVAILABLE_GRADERS = {cls.__name__: cls for cls in _GRADERS}
