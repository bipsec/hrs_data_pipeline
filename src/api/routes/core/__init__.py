"""Core codebook API routes: codebooks, variables, sections, search."""

from .codebooks import router as codebooks_router
from .variables import router as variables_router
from .sections import router as sections_router
from .search import router as search_router

__all__ = [
    "codebooks_router",
    "variables_router",
    "sections_router",
    "search_router",
]
