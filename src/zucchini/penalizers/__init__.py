from .exceptions import InvalidPenalizerConfigError
from .penalizer_interface import PenalizerInterface
from .late_penalizer import LatePenalizer
from .checkoff_penalizer import CheckoffPenalizer

__all__ = ['InvalidPenalizerConfigError', 'PenalizerInterface',
           'LatePenalizer', 'CheckoffPenalizer']

_PENALIZERS = (
    LatePenalizer,
    CheckoffPenalizer
)
AVAILABLE_PENALIZERS = {cls.__name__: cls for cls in _PENALIZERS}
