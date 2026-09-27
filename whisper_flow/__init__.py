"""whisper_flow — Backward-compatibility alias for freeflow."""

import warnings

warnings.warn(
    "The 'whisper_flow' package has been renamed to 'freeflow'. Please import from 'freeflow' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from freeflow import *  # noqa: F401, F403
