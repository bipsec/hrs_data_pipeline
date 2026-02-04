"""API route modules."""

from .general import router as general_router
from .codebooks import router as codebooks_router
from .variables import router as variables_router
from .sections import router as sections_router
from .search import router as search_router
from .utilities import router as utilities_router
from .categorizer import router as categorizer_router

__all__ = [
    "general_router",
    "codebooks_router",
    "variables_router",
    "sections_router",
    "search_router",
    "utilities_router",
    "categorizer_router",
]
