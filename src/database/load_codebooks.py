"""Load parsed HRS codebook data into MongoDB."""

import json
import re
import argparse
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .mongodb_client import MongoDBClient


def load_codebook_to_mongodb(
    codebook_path: Path,
    mongodb_client: MongoDBClient,
    collection_name: str = "codebooks",
    year: Optional[int] = None,
    source: Optional[str] = None,
) -> None:
    """Load a single codebook JSON file into MongoDB.
    
    Args:
        codebook_path: Path to codebook JSON file
        mongodb_client: MongoDB client instance
        collection_name: Name of MongoDB collection
        year: Year of the codebook (extracted from path if not provided)
        source: Source identifier (extracted from path if not provided)
    """
    if not codebook_path.exists():
        raise FileNotFoundError(f"Codebook file not found: {codebook_path}")
    
    # Extract year and source from path if not provided
    if year is None:
        # Try to extract from parent directory name
        parent = codebook_path.parent
        if parent.name.isdigit():
            year = int(parent.name)
        else:
            # Try from filename
            year_match = re.search(r"(\d{4})", codebook_path.stem)
            if year_match:
                year = int(year_match.group(1))
    
    if source is None:
        # Extract from path: data/parsed/{source}/{year}/codebook_{year}.json
        parts = codebook_path.parts
        if "parsed" in parts:
            parsed_idx = parts.index("parsed")
            if parsed_idx + 1 < len(parts):
                source = parts[parsed_idx + 1]
    
    print(f"Loading codebook: {codebook_path.name}")
    print(f"  Year: {year}, Source: {source}")
    
    # Load JSON file
    with open(codebook_path, "r", encoding="utf-8") as f:
        codebook_data = json.load(f)
    
    # Add metadata
    codebook_data["_loaded_at"] = datetime.now().isoformat()
    codebook_data["_file_path"] = str(codebook_path)
    
    # Get collection
    collection = mongodb_client.get_collection(collection_name)
    
    # Check if document already exists
    existing = collection.find_one({
        "year": year,
        "source": source or codebook_data.get("source"),
    })
    
    if existing:
        # Update existing document
        collection.update_one(
            {"_id": existing["_id"]},
            {"$set": codebook_data}
        )
        print(f"  Updated existing document (ID: {existing['_id']})")
    else:
        # Insert new document
        result = collection.insert_one(codebook_data)
        print(f"  Inserted new document (ID: {result.inserted_id})")
    
    # Load sections separately
    sections_dir = codebook_path.parent / "sections"
    if sections_dir.exists():
        load_sections_to_mongodb(
            sections_dir,
            mongodb_client,
            year=year,
            source=source or codebook_data.get("source"),
        )


def load_sections_to_mongodb(
    sections_dir: Path,
    mongodb_client: MongoDBClient,
    collection_name: str = "sections",
    year: Optional[int] = None,
    source: Optional[str] = None,
) -> None:
    """Load section JSON files into MongoDB.
    
    Args:
        sections_dir: Directory containing section JSON files
        mongodb_client: MongoDB client instance
        collection_name: Name of MongoDB collection
        year: Year of the codebook
        source: Source identifier
    """
    section_files = list(sections_dir.glob("section_*.json"))
    print(f"  Loading {len(section_files)} section files...")
    
    collection = mongodb_client.get_collection(collection_name)
    
    for section_file in section_files:
        with open(section_file, "r", encoding="utf-8") as f:
            section_data = json.load(f)
        
        # Extract section code from filename
        section_code = section_file.stem.replace("section_", "")
        
        # Add metadata
        section_data["_loaded_at"] = datetime.now().isoformat()
        section_data["_file_path"] = str(section_file)
        if year:
            section_data["year"] = year
        if source:
            section_data["source"] = source
        
        # Check if document exists
        existing = collection.find_one({
            "year": year,
            "source": source,
            "section.code": section_code,
        })
        
        if existing:
            collection.update_one(
                {"_id": existing["_id"]},
                {"$set": section_data}
            )
        else:
            collection.insert_one(section_data)
    
    print(f"  Loaded {len(section_files)} sections")


def load_variables_index_to_mongodb(
    index_path: Path,
    mongodb_client: MongoDBClient,
    collection_name: str = "variables_index",
    year: Optional[int] = None,
    source: Optional[str] = None,
) -> None:
    """Load variables index JSON file into MongoDB.
    
    Args:
        index_path: Path to variables_index.json file
        mongodb_client: MongoDB client instance
        collection_name: Name of MongoDB collection
        year: Year of the codebook
        source: Source identifier
    """
    if not index_path.exists():
        return
    
    print(f"Loading variables index: {index_path.name}")
    
    with open(index_path, "r", encoding="utf-8") as f:
        index_data = json.load(f)
    
    # Add metadata
    index_data["_loaded_at"] = datetime.now().isoformat()
    index_data["_file_path"] = str(index_path)
    
    collection = mongodb_client.get_collection(collection_name)
    
    # Check if document exists
    existing = collection.find_one({
        "year": year or index_data.get("year"),
        "source": source or index_data.get("source"),
    })
    
    if existing:
        collection.update_one(
            {"_id": existing["_id"]},
            {"$set": index_data}
        )
        print(f"  Updated existing index document")
    else:
        collection.insert_one(index_data)
        print(f"  Inserted new index document")


EXIT_SOURCE = "hrs_exit_codebook"
POST_EXIT_SOURCE = "hrs_post_exit_codebook"


def load_exit_codebooks(
    parsed_dir: Path,
    mongodb_client: MongoDBClient,
    year_filter: Optional[int] = None,
) -> int:
    """Load exit codebooks from parsed directory into MongoDB.

    Looks for parsed_dir / hrs_exit_codebook / {year} / codebook_{year}.json
    and loads each into the codebooks collection with source=hrs_exit_codebook.
    Also loads variables_index.json and section files when present.

    Args:
        parsed_dir: Directory containing parsed data (e.g. data/parsed)
        mongodb_client: MongoDB client instance
        year_filter: If set, load only this year

    Returns:
        Number of exit codebooks loaded.
    """
    exit_dir = parsed_dir / EXIT_SOURCE
    if not exit_dir.exists():
        print(f"Exit codebook directory not found: {exit_dir}")
        return 0

    codebook_files: List[tuple] = []
    for year_dir in exit_dir.iterdir():
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        year = int(year_dir.name)
        if year_filter is not None and year != year_filter:
            continue
        codebook_file = year_dir / f"codebook_{year}.json"
        if codebook_file.exists():
            codebook_files.append((codebook_file, year, EXIT_SOURCE))

    print(f"Found {len(codebook_files)} exit codebook(s) to load\n")
    for codebook_file, year, source in codebook_files:
        try:
            load_codebook_to_mongodb(
                codebook_file,
                mongodb_client,
                year=year,
                source=source,
            )
            index_file = codebook_file.parent / "variables_index.json"
            if index_file.exists():
                load_variables_index_to_mongodb(
                    index_file,
                    mongodb_client,
                    year=year,
                    source=source,
                )
            print()
        except Exception as e:
            print(f"  ERROR: Failed to load {codebook_file}: {e}")
            import traceback
            traceback.print_exc()
    return len(codebook_files)


def load_post_exit_codebooks(
    parsed_dir: Path,
    mongodb_client: MongoDBClient,
    year_filter: Optional[int] = None,
) -> int:
    """Load post-exit codebooks from parsed directory into MongoDB.

    Looks for parsed_dir / hrs_post_exit_codebook / {year} / codebook_{year}.json
    and loads each into the codebooks collection with source=hrs_post_exit_codebook.
    Also loads variables_index.json and section files when present.

    Args:
        parsed_dir: Directory containing parsed data (e.g. data/parsed)
        mongodb_client: MongoDB client instance
        year_filter: If set, load only this year

    Returns:
        Number of post-exit codebooks loaded.
    """
    post_exit_dir = parsed_dir / POST_EXIT_SOURCE
    if not post_exit_dir.exists():
        print(f"Post-exit codebook directory not found: {post_exit_dir}")
        return 0

    codebook_files: List[tuple] = []
    for year_dir in post_exit_dir.iterdir():
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        y = int(year_dir.name)
        if year_filter is not None and y != year_filter:
            continue
        codebook_file = year_dir / f"codebook_{y}.json"
        if codebook_file.exists():
            codebook_files.append((codebook_file, y, POST_EXIT_SOURCE))

    print(f"Found {len(codebook_files)} post-exit codebook(s) to load\n")
    for codebook_file, year, source in codebook_files:
        try:
            load_codebook_to_mongodb(
                codebook_file,
                mongodb_client,
                year=year,
                source=source,
            )
            index_file = codebook_file.parent / "variables_index.json"
            if index_file.exists():
                load_variables_index_to_mongodb(
                    index_file,
                    mongodb_client,
                    year=year,
                    source=source,
                )
            print()
        except Exception as e:
            print(f"  ERROR: Failed to load {codebook_file}: {e}")
            import traceback
            traceback.print_exc()
    return len(codebook_files)


def load_all_codebooks(
    parsed_dir: Path,
    mongodb_client: MongoDBClient,
    source_filter: Optional[str] = None,
    year_filter: Optional[int] = None,
) -> None:
    """Load all codebooks from parsed directory into MongoDB.

    Args:
        parsed_dir: Directory containing parsed codebooks
        mongodb_client: MongoDB client instance
        source_filter: Optional source name filter
        year_filter: Optional year filter
    """
    # Find all codebook JSON files
    codebook_files = []

    for source_dir in parsed_dir.iterdir():
        if not source_dir.is_dir():
            continue

        source_name = source_dir.name
        if source_filter and source_name != source_filter:
            continue

        for year_dir in source_dir.iterdir():
            if not year_dir.is_dir() or not year_dir.name.isdigit():
                continue

            year = int(year_dir.name)
            if year_filter and year != year_filter:
                continue

            codebook_file = year_dir / f"codebook_{year}.json"
            if codebook_file.exists():
                codebook_files.append((codebook_file, year, source_name))

    print(f"Found {len(codebook_files)} codebook file(s) to load\n")

    # Load each codebook
    for codebook_file, year, source in codebook_files:
        try:
            load_codebook_to_mongodb(
                codebook_file,
                mongodb_client,
                year=year,
                source=source,
            )

            # Also load variables index
            index_file = codebook_file.parent / "variables_index.json"
            if index_file.exists():
                load_variables_index_to_mongodb(
                    index_file,
                    mongodb_client,
                    year=year,
                    source=source,
                )

            print()  # Blank line between codebooks
        except Exception as e:
            print(f"  ERROR: Failed to load {codebook_file}: {e}")
            import traceback
            traceback.print_exc()
            continue


def create_indexes(mongodb_client: MongoDBClient) -> None:
    """Create indexes on MongoDB collections for better query performance.
    
    Args:
        mongodb_client: MongoDB client instance
    """
    print("Creating indexes...")
    
    # Indexes for codebooks collection
    mongodb_client.create_indexes("codebooks", [
        [("year", 1), ("source", 1)],
        [("source", 1)],
        [("year", 1)],
        [("total_variables", 1)],
    ])
    
    # Indexes for sections collection
    mongodb_client.create_indexes("sections", [
        [("year", 1), ("source", 1), ("section.code", 1)],
        [("section.code", 1)],
        [("year", 1)],
    ])
    
    # Indexes for variables_index collection
    mongodb_client.create_indexes("variables_index", [
        [("year", 1), ("source", 1)],
        [("variables.name", 1)],
        [("variables.section", 1)],
    ])
    
    print("Indexes created successfully")


def main():
    """Main entry point for loading codebooks into MongoDB."""
    parser = argparse.ArgumentParser(
        description="Load parsed HRS codebook data into MongoDB"
    )
    parser.add_argument(
        "--parsed-dir",
        type=Path,
        default=Path(__file__).parent.parent.parent / "data" / "parsed",
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
        "--connection-string",
        type=str,
        help="MongoDB connection string (overrides env vars)",
    )
    parser.add_argument(
        "--database-name",
        type=str,
        help="MongoDB database name (overrides env vars)",
    )
    parser.add_argument(
        "--create-indexes",
        action="store_true",
        help="Create indexes on collections",
    )
    parser.add_argument(
        "--exit-only",
        action="store_true",
        help="Load only exit codebooks (hrs_exit_codebook) from data/parsed/hrs_exit_codebook/",
    )
    parser.add_argument(
        "--post-exit-only",
        action="store_true",
        help="Load only post-exit codebooks (hrs_post_exit_codebook) from data/parsed/hrs_post_exit_codebook/",
    )

    args = parser.parse_args()

    # Connect to MongoDB
    with MongoDBClient(
        connection_string=args.connection_string,
        database_name=args.database_name,
    ) as client:
        # Create indexes if requested
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
            # Load codebooks (optionally filtered by --source and --year)
            load_all_codebooks(
                args.parsed_dir,
                client,
                source_filter=args.source,
                year_filter=args.year,
            )

            # Print summary
            codebooks_collection = client.get_collection("codebooks")
            count = codebooks_collection.count_documents({})
            print("=" * 60)
            print(f"Total codebooks in database: {count}")
            print(f"Database: {client.database_name}")


if __name__ == "__main__":
    main()
