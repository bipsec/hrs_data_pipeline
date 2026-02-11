"""MongoDB client for connecting and managing database operations."""

import os
import re
import urllib.parse
from pathlib import Path
from typing import Optional, Dict, Any
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection

try:
    import certifi
except ImportError:
    certifi = None  # type: ignore[assignment]


def load_dotenv(dotenv_path: Path) -> Dict[str, str]:
    """Load a .env file into a dictionary.
    
    Args:
        dotenv_path: Path to .env file
        
    Returns:
        Dictionary of key-value pairs from .env file
    """
    if not dotenv_path.exists():
        return {}
    
    values: Dict[str, str] = {}
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        # Skip empty lines, comments, and lines without '='
        if not line or line.startswith("#") or "=" not in line:
            continue
        
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        
        if key:
            values[key] = value
    
    return values


class MongoDBClient:
    """MongoDB client for database operations."""
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        database_name: Optional[str] = None,
        dotenv_path: Optional[Path] = None,
    ):
        """Initialize MongoDB client.
        
        Args:
            connection_string: MongoDB connection string (overrides env vars)
            database_name: Database name (overrides env vars)
            dotenv_path: Path to .env file (default: project root/.env)
        """
        if dotenv_path is None:
            # Default to project root
            project_root = Path(__file__).parent.parent.parent
            dotenv_path = project_root / ".env"
        
        env_vars = load_dotenv(dotenv_path)

        def _get(key: str, env_default: Optional[str] = None) -> Optional[str]:
            raw = os.getenv(key) or env_vars.get(key) or env_vars.get(key.lower()) or env_default
            return (raw.strip() or None) if raw else None

        # Connection string: explicit, or build from Atlas parts (same as load_codebook_to_mongodb_atlas)
        full_uri = (
            (connection_string.strip() or None) if connection_string else None
        ) or _get("MONGODB_CONNECTION_STRING")
        if full_uri:
            self.connection_string = full_uri
        else:
            user = _get("MONGODB_USER")
            pwd = _get("MONGODB_PASSWORD")
            cluster = _get("MONGODB_ATLAS_CLUSTER")
            if not cluster and _get("MONGODB_ATLAS_CONNECTION_STRING"):
                match = re.search(r"@([^/]+)", _get("MONGODB_ATLAS_CONNECTION_STRING") or "")
                if match:
                    cluster = match.group(1).rstrip("/")
            if user and pwd and cluster:
                encoded = urllib.parse.quote_plus(pwd)
                self.connection_string = f"mongodb+srv://{user}:{encoded}@{cluster}/"
            else:
                self.connection_string = "mongodb://localhost:27017/"

        # In hosted environments (e.g. Render), require explicit MongoDB config—do not use localhost
        if "localhost" in self.connection_string or "127.0.0.1" in self.connection_string:
            if os.getenv("RENDER") or os.getenv("PORT"):
                raise ConnectionError(
                    "MongoDB is set to localhost but this looks like a hosted environment. "
                    "Set MONGODB_CONNECTION_STRING (Atlas URI) or MONGODB_USER, MONGODB_PASSWORD, "
                    "and MONGODB_ATLAS_CLUSTER in your environment (e.g. Render Dashboard → Environment)."
                )

        # Database name: parameter, env, or default (MONGODB_DB or MONGODB_DATABASE_NAME)
        self.database_name = (
            database_name
            or _get("MONGODB_DATABASE_NAME")
            or _get("MONGODB_DB")
            or "hrs_data"
        )
        
        # Initialize client
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
    
    def connect(self) -> None:
        """Connect to MongoDB."""
        # Use certifi CA bundle for Atlas (mongodb+srv) to avoid SSL handshake errors
        kwargs: Dict[str, Any] = {}
        if "mongodb+srv://" in self.connection_string and certifi is not None:
            kwargs["tlsCAFile"] = certifi.where()
        try:
            self.client = MongoClient(self.connection_string, **kwargs)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            print(f"Connected to MongoDB: {self.database_name}")
        except Exception as e:
            msg = str(e)
            if "Connection refused" in msg and ("localhost" in self.connection_string or "127.0.0.1" in self.connection_string):
                raise ConnectionError(
                    f"Failed to connect to MongoDB: {e}. "
                    "To use MongoDB Atlas, set MONGODB_CONNECTION_STRING in .env (or env) to your Atlas URI, "
                    "e.g. mongodb+srv://user:password@cluster.mongodb.net/"
                ) from e
            raise ConnectionError(f"Failed to connect to MongoDB: {e}") from e
    
    def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
            print("Disconnected from MongoDB")
    
    def get_collection(self, collection_name: str) -> Collection:
        """Get a collection from the database.
        
        Args:
            collection_name: Name of the collection
            
        Returns:
            MongoDB Collection object
        """
        if self.db is None:
            raise RuntimeError("Not connected to database. Call connect() first.")
        return self.db[collection_name]
    
    def __enter__(self) -> "MongoDBClient":
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.disconnect()
    
    def create_indexes(self, collection_name: str, indexes: list) -> None:
        """Create indexes on a collection.
        
        Args:
            collection_name: Name of the collection
            indexes: List of index specifications
        """
        collection = self.get_collection(collection_name)
        for index_spec in indexes:
            collection.create_index(index_spec)
        print(f"Created indexes on {collection_name}")
