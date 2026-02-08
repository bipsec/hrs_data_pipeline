"""Shared API routes: general, utilities, categorizer."""

from .general import router as general_router
from .utilities import router as utilities_router
from .categorizer import router as categorizer_router

__all__ = [
    "general_router",
    "utilities_router",
    "categorizer_router",
]
