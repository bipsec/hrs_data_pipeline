"""MongoDB client for connecting and managing database operations."""

import os
from pathlib import Path
from typing import Optional, Dict
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection


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
        
        # Load environment variables
        env_vars = load_dotenv(dotenv_path)
        
        # Get connection string from parameter, env var, or .env file
        self.connection_string = (
            connection_string
            or os.getenv("MONGODB_CONNECTION_STRING")
            or env_vars.get("MONGODB_CONNECTION_STRING")
            or "mongodb://localhost:27017/"
        )
        
        # Get database name from parameter, env var, or .env file
        self.database_name = (
            database_name
            or os.getenv("MONGODB_DATABASE_NAME")
            or env_vars.get("MONGODB_DATABASE_NAME")
            or "hrs_data"
        )
        
        # Initialize client
        self.client: Optional[MongoClient] = None
        self.db: Optional[Database] = None
    
    def connect(self) -> None:
        """Connect to MongoDB."""
        try:
            self.client = MongoClient(self.connection_string)
            # Test connection
            self.client.admin.command('ping')
            self.db = self.client[self.database_name]
            print(f"Connected to MongoDB: {self.database_name}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {e}")
    
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
