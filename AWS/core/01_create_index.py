"""Create OpenSearch index for HRS Core data description chunks on JetStream2.

Index uses knn_vector for semantic search (HNSW via nmslib) and
standard text fields for BM25 lexical search.

Connects to local OpenSearch via basic auth.
"""
import os
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv
from opensearchpy import OpenSearch

load_dotenv()

# ---- OpenSearch config ----
OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "http://localhost:9200")
OPENSEARCH_USER = os.getenv("OPENSEARCH_USER", "admin")
OPENSEARCH_PASSWORD = os.getenv("OPENSEARCH_PASSWORD", "admin")
OS_INDEX = os.getenv("OS_INDEX", "hrs_core_data_desc")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))


def os_client() -> OpenSearch:
    parsed = urlparse(OPENSEARCH_HOST)
    host = parsed.hostname or "localhost"
    port = parsed.port or 9200
    use_ssl = parsed.scheme == "https"
    return OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_auth=(OPENSEARCH_USER, OPENSEARCH_PASSWORD),
        use_ssl=use_ssl,
        verify_certs=False,
        timeout=120,
    )


MAPPING = {
    "settings": {
        "index": {
            "knn": True,
            "knn.algo_param.ef_search": 512,
        }
    },
    "mappings": {
        "properties": {
            "chunk_id": {"type": "keyword"},
            "year": {"type": "integer"},
            "wave": {"type": "keyword"},
            "doc_type": {"type": "keyword"},
            "section_number": {"type": "keyword"},
            "heading_name": {"type": "keyword"},
            "page_range": {"type": "keyword"},
            "content_type": {"type": "keyword"},
            "source_file": {"type": "keyword"},

            # Searchable text (BM25)
            "content": {"type": "text"},

            # KNN vector for semantic search
            "embedding": {
                "type": "knn_vector",
                "dimension": EMBEDDING_DIM,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 512,
                        "m": 16,
                    },
                },
            },
        }
    },
}


if __name__ == "__main__":
    client = os_client()

    try:
        info = client.info()
        version = info.get("version", {}).get("number", "unknown")
        print(f"Connected to OpenSearch {version} at {OPENSEARCH_HOST}")
    except Exception as e:
        print(f"ERROR: Cannot connect to OpenSearch at {OPENSEARCH_HOST}: {e}")
        sys.exit(1)

    try:
        if client.indices.exists(index=OS_INDEX):
            print(f"Index already exists: {OS_INDEX}")
        else:
            client.indices.create(index=OS_INDEX, body=MAPPING)
            print(f"Created index: {OS_INDEX}")
    except Exception as e:
        print(f"ERROR: Failed to create/check index: {e}")
        sys.exit(1)
