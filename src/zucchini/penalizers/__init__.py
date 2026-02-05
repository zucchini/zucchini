from .exceptions import InvalidPenalizerConfigError
from .penalizer_interface import PenalizerInterface
from .late_penalizer import LatePenalizer

__all__ = ['InvalidPenalizerConfigError', 'PenalizerInterface',
           'LatePenalizer']

_PENALIZERS = (
    LatePenalizer,
)
AVAILABLE_PENALIZERS = {cls.__name__: cls for cls in _PENALIZERS}
