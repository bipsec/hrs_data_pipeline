"""API route modules (modular: core, exit, shared)."""

from .core import (
    codebooks_router,
    variables_router,
    sections_router,
    search_router,
)
from .exit import exit_router
from .shared import (
    general_router,
    utilities_router,
    categorizer_router,
)

from .coreSupplement import core_supplement_router

from .coreImputations import core_imputations_router
from .exitImputations import exit_imputations_router

from .aheadCore import ahead_core_router
from .aheadExit import ahead_exit_router
from .aheadCoreImputations import ahead_core_imputations_router
from .aheadExitImputations import ahead_exit_imputations_router

__all__ = [
    "general_router",
    "codebooks_router",
    "variables_router",
    "sections_router",
    "search_router",
    "utilities_router",
    "categorizer_router",
    "exit_router",
    "core_supplement_router",
    "core_imputations_router",
    "exit_imputations_router",
    "ahead_core_router",
    "ahead_exit_router",
    "ahead_core_imputations_router",
    "ahead_exit_imputations_router",
]
