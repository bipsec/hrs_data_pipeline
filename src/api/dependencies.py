"""FastAPI dependencies (e.g. DB client)."""

from ..database.mongodb_client import MongoDBClient


def get_mongodb_client() -> MongoDBClient:
    """Return MongoDB client instance (use as context manager in routes)."""
    return MongoDBClient()
