"""
MongoDB client for connecting and managing database operations.

Key improvements for hosted envs (Render):
- Stronger Atlas TLS defaults using certifi CA bundle
- Optional SSLContext forcing TLSv1.2+ (helps in some networks)
- Safe URI handling (avoid risky rewriting)
- Singleton client reuse helpers to avoid per-request MongoClient creation (memory + socket spike)
"""

from __future__ import annotations

import os
import re
import ssl
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

try:
    import certifi
except ImportError:
    certifi = None  # type: ignore[assignment]


def load_dotenv(dotenv_path: Path) -> Dict[str, str]:
    """Load a .env file into a dictionary (minimal parser)."""
    if not dotenv_path.exists():
        return {}

    values: Dict[str, str] = {}
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            values[key] = value

    return values


def _safe_uri(uri: str) -> str:
    """Redact password in URI for logs."""
    # mongodb+srv://user:pass@host/...
    return re.sub(r"(mongodb(?:\+srv)?://[^:]+):[^@]+@", r"\1:***@", uri)


class MongoDBClient:
    """MongoDB client for database operations."""

    def __init__(
        self,
        connection_string: Optional[str] = None,
        database_name: Optional[str] = None,
        dotenv_path: Optional[Path] = None,
    ):
        if dotenv_path is None:
            project_root = Path(__file__).parent.parent.parent
            dotenv_path = project_root / ".env"

        env_vars = load_dotenv(dotenv_path)

        def _get(key: str, env_default: Optional[str] = None) -> Optional[str]:
            raw = os.getenv(key) or env_vars.get(key) or env_vars.get(key.lower()) or env_default
            return (raw.strip() or None) if raw else None

        # ---- Connection String Resolution ----
        # Preferred: full URI provided explicitly or via env var.
        full_uri = ((connection_string.strip() or None) if connection_string else None) or _get(
            "MONGODB_CONNECTION_STRING"
        )

        if full_uri:
            self.connection_string = full_uri
        else:
            # Fallback: build Atlas URI from parts (Option B).
            user = _get("MONGODB_USER")
            pwd = _get("MONGODB_PASSWORD")
            cluster = _get("MONGODB_ATLAS_CLUSTER")

            if not cluster and _get("MONGODB_ATLAS_CONNECTION_STRING"):
                match = re.search(r"@([^/]+)", _get("MONGODB_ATLAS_CONNECTION_STRING") or "")
                if match:
                    cluster = match.group(1).rstrip("/")

            if user and pwd and cluster:
                encoded_pwd = urllib.parse.quote_plus(pwd)
                # NOTE: DB name will be handled separately; keep URI clean.
                self.connection_string = f"mongodb+srv://{user}:{encoded_pwd}@{cluster}/"
            else:
                self.connection_string = "mongodb://localhost:27017/"

        # Hosted safety guard: never allow localhost on Render
        if ("localhost" in self.connection_string or "127.0.0.1" in self.connection_string) and (
            os.getenv("RENDER") or os.getenv("PORT")
        ):
            raise ConnectionError(
                "MongoDB is set to localhost but this looks like a hosted environment. "
                "Set MONGODB_CONNECTION_STRING (Atlas URI) OR set MONGODB_USER, MONGODB_PASSWORD, "
                "and MONGODB_ATLAS_CLUSTER in Render Dashboard → Environment."
            )

        # ---- Database Name ----
        raw_db = (
            (database_name.strip() or None) if database_name else None
        ) or _get("MONGODB_DATABASE_NAME") or _get("MONGODB_DB")

        if not raw_db or raw_db in ("/", "\\") or not raw_db.replace("/", "").replace("\\", "").strip():
            raw_db = "hrs_data"

        self.database_name = raw_db

        # ---- Client state ----
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None

    def _build_tls_kwargs(self) -> Dict[str, Any]:
        """
        Build kwargs for MongoClient.
        For Atlas, force TLS with certifi CA bundle.
        Optionally force TLS >= 1.2 with SSLContext.
        """
        uri = self.connection_string
        is_atlas = uri.startswith("mongodb+srv://") or "mongodb.net" in uri

        kwargs: Dict[str, Any] = {
            "serverSelectionTimeoutMS": 30000,
            "connectTimeoutMS": 20000,
            "socketTimeoutMS": 20000,
        }

        if is_atlas:
            if certifi is None:
                raise RuntimeError(
                    "certifi is required for TLS connections to MongoDB Atlas. "
                    "Add `certifi` to your dependencies."
                )

            kwargs["tls"] = True
            kwargs["tlsCAFile"] = certifi.where()

            # Optional: force TLSv1.2+ (sometimes helps with weird middleboxes)
            ctx = ssl.create_default_context(cafile=certifi.where())
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            kwargs["ssl_context"] = ctx

        return kwargs

    def connect(self) -> None:
        """Connect to MongoDB and select database."""
        try:
            kwargs = self._build_tls_kwargs()
            # Helpful log (safe)
            print("MongoDB URI (safe):", _safe_uri(self.connection_string))

            self.client = MongoClient(self.connection_string, **kwargs)
            self.client.admin.command("ping")
            self.db = self.client[self.database_name]
            print(f"Connected to MongoDB database: {self.database_name}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {e}") from e

    def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
        self.client = None
        self.db = None
        print("Disconnected from MongoDB")

    def get_collection(self, collection_name: str) -> Collection:
        """Get a collection from the database."""
        if self.db is None:
            raise RuntimeError("Not connected to database. Call connect() first.")
        return self.db[collection_name]

    def create_indexes(self, collection_name: str, indexes: list) -> None:
        """Create indexes on a collection."""
        collection = self.get_collection(collection_name)
        for index_spec in indexes:
            collection.create_index(index_spec)
        print(f"Created indexes on {collection_name}")

    def __enter__(self) -> "MongoDBClient":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.disconnect()


# ------------------------------------------------------------------------------
# Singleton helpers (RECOMMENDED FOR FASTAPI ON RENDER)
# ------------------------------------------------------------------------------
_GLOBAL: Optional[MongoDBClient] = None


def get_global_mongo() -> MongoDBClient:
    """
    Return a singleton MongoDBClient.

    Use this in FastAPI so you don't create a new MongoClient per request,
    which can cause memory spikes + TLS overhead.
    """
    global _GLOBAL
    if _GLOBAL is None:
        _GLOBAL = MongoDBClient()
        _GLOBAL.connect()
    return _GLOBAL


def close_global_mongo() -> None:
    """Close the singleton client (call on app shutdown)."""
    global _GLOBAL
    if _GLOBAL is not None:
        _GLOBAL.disconnect()
    _GLOBAL = None
