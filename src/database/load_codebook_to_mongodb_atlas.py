"""Load parsed HRS codebook data into MongoDB Atlas using credentials from .env."""

import argparse
import re
import urllib.parse
from pathlib import Path

from .mongodb_client import MongoDBClient, load_dotenv
from .load_codebooks import (
    load_all_codebooks,
    load_exit_codebooks,
    load_post_exit_codebooks,
    create_indexes,
)


def get_atlas_connection_string(dotenv_path: Path) -> tuple[str, str]:
    """Build MongoDB Atlas connection string and database name from .env.

    Reads MONGODB_USER, MONGODB_PASSWORD (required), MONGODB_DB or MONGODB_DATABASE_NAME,
    and either MONGODB_ATLAS_CLUSTER (e.g. cluster0.xxxx.mongodb.net) or
    MONGODB_ATLAS_CONNECTION_STRING (used to extract cluster host if no credentials in it).

    Returns:
        (connection_string, database_name)
    """
    env = load_dotenv(dotenv_path)
    user = env.get("MONGODB_USER") or env.get("mongodb_user")
    password = env.get("MONGODB_PASSWORD") or env.get("mongodb_password")
    if not user or not password:
        raise ValueError(
            "Missing MongoDB Atlas credentials. Set MONGODB_USER and MONGODB_PASSWORD in .env"
        )

    database_name = (
        env.get("MONGODB_DB")
        or env.get("MONGODB_DATABASE_NAME")
        or "hrs_data"
    )

    cluster = env.get("MONGODB_ATLAS_CLUSTER")
    if not cluster:
        # Try to extract host from MONGODB_ATLAS_CONNECTION_STRING (e.g. cluster0.xxx.mongodb.net)
        atlas_uri = env.get("MONGODB_ATLAS_CONNECTION_STRING") or ""
        match = re.search(r"@([^/]+)", atlas_uri)
        if match:
            cluster = match.group(1).rstrip("/")
        if not cluster:
            raise ValueError(
                "Missing Atlas cluster. Set MONGODB_ATLAS_CLUSTER in .env "
                "(e.g. cluster0.xxxx.mongodb.net) or provide MONGODB_ATLAS_CONNECTION_STRING"
            )

    encoded_password = urllib.parse.quote_plus(password)
    connection_string = f"mongodb+srv://{user}:{encoded_password}@{cluster}/{database_name}"
    return connection_string, database_name


def main() -> None:
    """Load codebooks into MongoDB Atlas using .env credentials."""
    project_root = Path(__file__).resolve().parent.parent.parent
    dotenv_path = project_root / ".env"

    if not dotenv_path.exists():
        raise SystemExit(f".env not found at {dotenv_path}")

    try:
        connection_string, database_name = get_atlas_connection_string(dotenv_path)
    except ValueError as e:
        raise SystemExit(str(e))

    parser = argparse.ArgumentParser(
        description="Load parsed HRS codebook data into MongoDB Atlas (credentials from .env)"
    )
    parser.add_argument(
        "--parsed-dir",
        type=Path,
        default=project_root / "data" / "parsed",
        help="Directory containing parsed codebook JSON files",
    )
    parser.add_argument(
        "--source",
        type=str,
        help="Load only specific source (e.g., hrs_core_codebook)",
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Load only specific year",
    )
    parser.add_argument(
        "--create-indexes",
        action="store_true",
        help="Create indexes on collections",
    )
    parser.add_argument(
        "--exit-only",
        action="store_true",
        help="Load only exit codebooks (hrs_exit_codebook)",
    )
    parser.add_argument(
        "--post-exit-only",
        action="store_true",
        help="Load only post-exit codebooks (hrs_post_exit_codebook)",
    )
    args = parser.parse_args()

    print("Using MongoDB Atlas (credentials from .env)")
    print(f"  Database: {database_name}\n")

    with MongoDBClient(
        connection_string=connection_string,
        database_name=database_name,
        dotenv_path=dotenv_path,
    ) as client:
        if args.create_indexes:
            create_indexes(client)
            print()

        if args.exit_only:
            n = load_exit_codebooks(
                args.parsed_dir,
                client,
                year_filter=args.year,
            )
            print("=" * 60)
            print(f"Loaded {n} exit codebook(s)")
            print(f"Database: {client.database_name}")
        elif args.post_exit_only:
            n = load_post_exit_codebooks(
                args.parsed_dir,
                client,
                year_filter=args.year,
            )
            print("=" * 60)
            print(f"Loaded {n} post-exit codebook(s)")
            print(f"Database: {client.database_name}")
        else:
            load_all_codebooks(
                args.parsed_dir,
                client,
                source_filter=args.source,
                year_filter=args.year,
            )
            codebooks_collection = client.get_collection("codebooks")
            count = codebooks_collection.count_documents({})
            print("=" * 60)
            print(f"Total codebooks in database: {count}")
            print(f"Database: {client.database_name}")


if __name__ == "__main__":
    main()
