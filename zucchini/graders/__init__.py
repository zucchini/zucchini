from .exceptions import InvalidGraderConfigError
from .grader_interface import GraderInterface, PartGrade, Part
from .prompt_grader import PromptGrader
from .open_file_grader import OpenFileGrader

__all__ = ['InvalidGraderConfigError', 'GraderInterface', 'Part', 'PartGrade',
           'PromptGrader', 'OpenFileGrader']

_GRADERS = (
    PromptGrader,
    OpenFileGrader,
)
AVAILABLE_GRADERS = {cls.__name__: cls for cls in _GRADERS}
