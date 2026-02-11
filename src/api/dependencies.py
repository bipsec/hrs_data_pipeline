from __future__ import annotations

from typing import Optional

from ..database.mongodb_client import MongoDBClient

# One process-wide client (1 per Render instance)
_GLOBAL_CLIENT: Optional[MongoDBClient] = None


def get_mongodb_client() -> MongoDBClient:
    """
    Return a singleton MongoDB client instance.

    IMPORTANT:
    - Do NOT use this as a context manager inside routes (no `with ... as client:`).
    - Create the connection once at app startup, reuse for all requests.
    """
    global _GLOBAL_CLIENT
    if _GLOBAL_CLIENT is None:
        _GLOBAL_CLIENT = MongoDBClient()
        _GLOBAL_CLIENT.connect()
    return _GLOBAL_CLIENT


def close_mongodb_client() -> None:
    """Close the singleton client (call on app shutdown)."""
    global _GLOBAL_CLIENT
    if _GLOBAL_CLIENT is not None:
        _GLOBAL_CLIENT.disconnect()
    _GLOBAL_CLIENT = None
