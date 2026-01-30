"""Tests for HRS data pipeline: parse, database, and API functionality."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

from src.parse.parse_txt_codebook import parse_txt_codebook, _extract_year_from_filename
from src.parse.parse_codebooks import find_codebook_files
from src.parse.models import Codebook, Variable, Section, VariableLevel, VariableType
from src.database.mongodb_client import MongoDBClient, load_dotenv
from src.database.load_codebooks import (
    load_codebook_to_mongodb,
    load_all_codebooks,
    create_indexes,
)
from src.api.app import app
from fastapi.testclient import TestClient


# ===== PARSE TESTS =====

def test_extract_year_from_filename():
    """Test year extraction from filename."""
    assert _extract_year_from_filename(Path("h2020cb.txt")) == 2020
    assert _extract_year_from_filename(Path("h1998cb.txt")) == 1998
    assert _extract_year_from_filename(Path("codebook_2020.txt")) == 2020


def test_parse_txt_codebook_basic(tmp_path: Path):
    """Test parsing a basic codebook file."""
    # Create a simple codebook file
    codebook_content = """
SECTION A: DEMOGRAPHICS

VAR1                          Variable 1 Description
                              Type: Numeric  Width: 8  Decimals: 0
                              0 = No
                              1 = Yes

VAR2                          Variable 2 Description
                              Type: Character  Width: 10
                              Blank = Missing
    """
    
    codebook_file = tmp_path / "test_codebook.txt"
    codebook_file.write_text(codebook_content, encoding="utf-8")
    
    codebook = parse_txt_codebook(codebook_file, source="test_source", year=2020)
    
    assert codebook.source == "test_source"
    assert codebook.year == 2020
    assert codebook.total_variables >= 0
    assert isinstance(codebook.sections, list)


def test_parse_txt_codebook_file_not_found():
    """Test parsing non-existent file raises error."""
    with pytest.raises(FileNotFoundError):
        parse_txt_codebook(Path("nonexistent.txt"))


def test_find_codebook_files(tmp_path: Path):
    """Test finding codebook files in directory structure."""
    # Create directory structure: data/HRS Data/2020/Core/h2020cb/h2020cb.txt
    data_dir = tmp_path / "data"
    hrs_data = data_dir / "HRS Data" / "2020" / "Core" / "h2020cb"
    hrs_data.mkdir(parents=True)
    
    codebook_file = hrs_data / "h2020cb.txt"
    codebook_file.write_text("test content")
    
    files = find_codebook_files(data_dir, year=2020)
    assert len(files) > 0
    assert codebook_file in files


def test_find_codebook_files_no_year(tmp_path: Path):
    """Test finding codebook files without year filter."""
    # Create multiple year directories
    for year in [2020, 2018]:
        hrs_data = tmp_path / "data" / "HRS Data" / str(year) / "Core" / f"h{year}cb"
        hrs_data.mkdir(parents=True)
        (hrs_data / f"h{year}cb.txt").write_text("test")
    
    files = find_codebook_files(tmp_path / "data")
    assert len(files) >= 2


# ===== DATABASE CONFIG TESTS =====

def test_load_dotenv(tmp_path: Path):
    """Test loading .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text("""
MONGODB_CONNECTION_STRING=mongodb://localhost:27017/
MONGODB_DATABASE_NAME=test_db
# This is a comment
EMPTY_VAR=
    """)
    
    env_vars = load_dotenv(env_file)
    
    assert env_vars["MONGODB_CONNECTION_STRING"] == "mongodb://localhost:27017/"
    assert env_vars["MONGODB_DATABASE_NAME"] == "test_db"
    assert "EMPTY_VAR" in env_vars
    assert env_vars["EMPTY_VAR"] == ""


def test_load_dotenv_nonexistent(tmp_path: Path):
    """Test loading non-existent .env file returns empty dict."""
    env_vars = load_dotenv(tmp_path / "nonexistent.env")
    assert env_vars == {}


def test_mongodb_client_initialization():
    """Test MongoDB client initialization."""
    client = MongoDBClient(
        connection_string="mongodb://localhost:27017/",
        database_name="test_db"
    )
    
    assert client.connection_string == "mongodb://localhost:27017/"
    assert client.database_name == "test_db"
    assert client.client is None  # Not connected yet


def test_mongodb_client_context_manager():
    """Test MongoDB client as context manager."""
    with patch('src.database.mongodb_client.MongoClient') as mock_mongo:
        mock_client = MagicMock()
        mock_mongo.return_value = mock_client
        mock_client.__getitem__.return_value = MagicMock()
        
        with MongoDBClient(
            connection_string="mongodb://localhost:27017/",
            database_name="test_db"
        ) as client:
            assert client.client is not None
        
        # Should disconnect on exit
        mock_client.close.assert_called_once()


def test_mongodb_client_get_collection():
    """Test getting a collection from MongoDB client."""
    with patch('src.database.mongodb_client.MongoClient') as mock_mongo:
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        
        mock_mongo.return_value = mock_client
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        with MongoDBClient(
            connection_string="mongodb://localhost:27017/",
            database_name="test_db"
        ) as client:
            collection = client.get_collection("test_collection")
            assert collection is not None
            mock_db.__getitem__.assert_called_with("test_collection")


# ===== DATABASE LOAD TESTS =====

def test_load_codebook_to_mongodb(tmp_path: Path):
    """Test loading a codebook JSON into MongoDB."""
    # Create a test codebook JSON
    codebook_data = {
        "source": "test_source",
        "year": 2020,
        "total_variables": 10,
        "total_sections": 2,
        "sections": [],
        "variables": []
    }
    
    codebook_file = tmp_path / "codebook_2020.json"
    codebook_file.write_text(json.dumps(codebook_data), encoding="utf-8")
    
    # Mock MongoDB client
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.get_collection.return_value = mock_collection
    mock_collection.find_one.return_value = None  # No existing document
    mock_collection.insert_one.return_value = MagicMock()
    
    load_codebook_to_mongodb(
        codebook_file,
        mock_client,
        year=2020,
        source="test_source"
    )
    
    # Verify insert was called
    mock_collection.insert_one.assert_called_once()
    inserted_doc = mock_collection.insert_one.call_args[0][0]
    assert inserted_doc["year"] == 2020
    assert inserted_doc["source"] == "test_source"


def test_load_codebook_to_mongodb_file_not_found():
    """Test loading non-existent codebook file raises error."""
    mock_client = MagicMock()
    
    with pytest.raises(FileNotFoundError):
        load_codebook_to_mongodb(
            Path("nonexistent.json"),
            mock_client
        )


def test_load_all_codebooks(tmp_path: Path):
    """Test loading all codebooks from directory."""
    # Create directory structure: parsed/test_source/2020/codebook_2020.json
    parsed_dir = tmp_path / "parsed"
    source_dir = parsed_dir / "test_source" / "2020"
    source_dir.mkdir(parents=True)
    
    codebook_file = source_dir / "codebook_2020.json"
    codebook_data = {
        "source": "test_source",
        "year": 2020,
        "total_variables": 10,
        "sections": [],
        "variables": []
    }
    codebook_file.write_text(json.dumps(codebook_data), encoding="utf-8")
    
    # Mock MongoDB client
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.get_collection.return_value = mock_collection
    mock_collection.find_one.return_value = None
    mock_collection.insert_one.return_value = MagicMock()
    
    load_all_codebooks(parsed_dir, mock_client)
    
    # Verify codebook was loaded
    assert mock_collection.insert_one.called


def test_create_indexes():
    """Test creating indexes on MongoDB collections."""
    mock_client = MagicMock()
    
    # Mock the create_indexes method on MongoDBClient
    mock_client.create_indexes = MagicMock()
    
    create_indexes(mock_client)
    
    # Verify create_indexes was called for all three collections
    assert mock_client.create_indexes.call_count == 3
    
    # Verify it was called with correct collection names
    calls = [call[0][0] for call in mock_client.create_indexes.call_args_list]
    assert "codebooks" in calls
    assert "sections" in calls
    assert "variables_index" in calls


# ===== API TESTS =====

@pytest.fixture
def api_client():
    """Create a test client for the API."""
    return TestClient(app)


@pytest.fixture
def mock_mongodb_client():
    """Create a mock MongoDB client for API tests."""
    with patch('src.api.app.get_mongodb_client') as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value.__enter__.return_value = mock_client
        mock_get_client.return_value.__exit__.return_value = None
        
        # Setup default mock collections
        mock_codebooks_collection = MagicMock()
        mock_sections_collection = MagicMock()
        mock_index_collection = MagicMock()
        
        def get_collection_side_effect(name):
            if name == "codebooks":
                return mock_codebooks_collection
            elif name == "sections":
                return mock_sections_collection
            elif name == "variables_index":
                return mock_index_collection
            return MagicMock()
        
        mock_client.get_collection.side_effect = get_collection_side_effect
        
        yield {
            "client": mock_client,
            "codebooks": mock_codebooks_collection,
            "sections": mock_sections_collection,
            "index": mock_index_collection,
        }


def test_api_root_endpoint(api_client, mock_mongodb_client):
    """Test root endpoint."""
    response = api_client.get("/")
    assert response.status_code in [200, 404]  # 200 if UI exists, 404 if not


def test_api_stats_endpoint(api_client, mock_mongodb_client):
    """Test stats endpoint."""
    mocks = mock_mongodb_client
    
    # Setup mock data
    mocks["codebooks"].count_documents.return_value = 5
    mocks["sections"].count_documents.return_value = 20
    mocks["index"].count_documents.return_value = 5
    mocks["codebooks"].find.return_value = [
        {"total_variables": 100},
        {"total_variables": 200},
    ]
    mocks["codebooks"].distinct.return_value = [2020, 2018]
    
    response = api_client.get("/stats")
    
    assert response.status_code == 200
    data = response.json()
    assert "total_codebooks" in data
    assert "total_variables" in data
    assert "year_range" in data


def test_api_years_endpoint(api_client, mock_mongodb_client):
    """Test years endpoint."""
    mocks = mock_mongodb_client
    
    mocks["codebooks"].distinct.side_effect = lambda field: {
        "year": [2020, 2018, 2016],
        "source": ["hrs_core_codebook", "hrs_exit_codebook"]
    }.get(field, [])
    
    response = api_client.get("/years")
    
    assert response.status_code == 200
    data = response.json()
    assert "years" in data
    assert "sources" in data
    assert len(data["years"]) > 0
    assert len(data["sources"]) > 0


def test_api_codebooks_endpoint(api_client, mock_mongodb_client):
    """Test codebooks endpoint."""
    mocks = mock_mongodb_client
    
    mocks["codebooks"].find.return_value = [
        {
            "source": "hrs_core_codebook",
            "year": 2020,
            "release_type": "Final",
            "total_variables": 100,
            "total_sections": 5,
            "levels": ["Household", "Respondent"]
        }
    ]
    
    response = api_client.get("/codebooks")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["source"] == "hrs_core_codebook"
    assert data[0]["year"] == 2020


def test_api_codebooks_with_filters(api_client, mock_mongodb_client):
    """Test codebooks endpoint with year and source filters."""
    mocks = mock_mongodb_client
    
    mocks["codebooks"].find.return_value = [
        {
            "source": "hrs_core_codebook",
            "year": 2020,
            "total_variables": 100,
            "total_sections": 5,
            "levels": []
        }
    ]
    
    response = api_client.get("/codebooks?year=2020&source=hrs_core_codebook")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0


def test_api_codebook_by_year(api_client, mock_mongodb_client):
    """Test getting codebook by year."""
    mocks = mock_mongodb_client
    
    mocks["codebooks"].find_one.return_value = {
        "source": "hrs_core_codebook",
        "year": 2020,
        "total_variables": 100,
        "total_sections": 5,
        "levels": []
    }
    
    response = api_client.get("/codebooks/2020?source=hrs_core_codebook")
    
    assert response.status_code == 200
    data = response.json()
    assert data["year"] == 2020
    assert data["source"] == "hrs_core_codebook"


def test_api_codebook_not_found(api_client, mock_mongodb_client):
    """Test getting non-existent codebook returns 404."""
    mocks = mock_mongodb_client
    
    mocks["codebooks"].find_one.return_value = None
    
    response = api_client.get("/codebooks/9999?source=hrs_core_codebook")
    
    assert response.status_code == 404


def test_api_search_variables(api_client, mock_mongodb_client):
    """Test search variables endpoint."""
    mocks = mock_mongodb_client
    
    # Mock variables index
    mocks["index"].find_one.return_value = {
        "variables": [
            {
                "name": "VAR1",
                "year": 2020,
                "section": "A",
                "level": "Respondent",
                "description": "Test variable",
                "type": "Numeric"
            }
        ]
    }
    
    response = api_client.get("/search?q=VAR1")
    
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "total" in data
    assert data["query"] == "VAR1"


def test_api_search_variables_no_results(api_client, mock_mongodb_client):
    """Test search with no results."""
    mocks = mock_mongodb_client
    
    mocks["index"].find_one.return_value = None
    
    # Fallback to codebooks
    mocks["codebooks"].find.return_value = []
    
    response = api_client.get("/search?q=nonexistent")
    
    # Should return 404 or empty results
    assert response.status_code in [200, 404]


def test_api_sections_endpoint(api_client, mock_mongodb_client):
    """Test sections endpoint."""
    mocks = mock_mongodb_client
    
    mocks["codebooks"].find_one.return_value = {
        "sections": [
            {
                "code": "A",
                "name": "Demographics",
                "level": "Respondent",
                "year": 2020,
                "variable_count": 10,
                "variables": ["VAR1", "VAR2"]
            }
        ]
    }
    
    response = api_client.get("/sections?year=2020&source=hrs_core_codebook")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["code"] == "A"


def test_api_variables_endpoint(api_client, mock_mongodb_client):
    """Test variables endpoint."""
    mocks = mock_mongodb_client
    
    mocks["codebooks"].find_one.return_value = {
        "variables": [
            {
                "name": "VAR1",
                "year": 2020,
                "section": "A",
                "level": "Respondent",
                "description": "Test variable",
                "type": "Numeric"
            }
        ]
    }
    
    response = api_client.get("/variables?year=2020&source=hrs_core_codebook")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert data[0]["name"] == "VAR1"


def test_api_variable_detail(api_client, mock_mongodb_client):
    """Test getting variable details."""
    mocks = mock_mongodb_client
    
    mocks["codebooks"].find_one.return_value = {
        "variables": [
            {
                "name": "VAR1",
                "year": 2020,
                "section": "A",
                "level": "Respondent",
                "description": "Test variable",
                "type": "Numeric",
                "width": 8,
                "decimals": 0
            }
        ]
    }
    
    response = api_client.get("/variables/VAR1?year=2020&source=hrs_core_codebook")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "VAR1"
    assert data["year"] == 2020
