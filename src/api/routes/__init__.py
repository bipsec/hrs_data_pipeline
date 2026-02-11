"""API route modules (modular: core, exit, shared)."""

from .core import (
    codebooks_router,
    variables_router,
    sections_router,
    search_router,
)
from .exit import exit_router
from .post_exit import post_exit_router
from .shared import (
    general_router,
    utilities_router,
    categorizer_router,
)

__all__ = [
    "general_router",
    "codebooks_router",
    "variables_router",
    "sections_router",
    "search_router",
    "utilities_router",
    "categorizer_router",
    "exit_router",
    "post_exit_router",
]
