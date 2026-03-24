"""Embed HRS Core data description chunks and bulk-index into OpenSearch on JetStream2.

Reads AWS/data/core/*.json (organized by prepare_data.py),
embeds via sentence-transformers (BAAI/bge-large-en-v1.5), and bulk-indexes
into the HRS core data description index.
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List
from urllib.parse import urlparse

from dotenv import load_dotenv
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

load_dotenv()

# ---- Config ----
script_dir = Path(__file__).resolve().parent
default_data_dir = script_dir.parent / "data" / "core"
CORE_DATA_DIR = os.getenv("CORE_DATA_DIR", str(default_data_dir))

OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "http://localhost:9200")
OPENSEARCH_USER = os.getenv("OPENSEARCH_USER", "admin")
OPENSEARCH_PASSWORD = os.getenv("OPENSEARCH_PASSWORD", "admin")
OS_INDEX = os.getenv("OS_INDEX", "hrs_core_data_desc")

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))

BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "64"))
OS_BULK_FLUSH = int(os.getenv("ES_BULK_FLUSH", "2000"))
OS_REQUEST_TIMEOUT = int(os.getenv("OS_REQUEST_TIMEOUT", "120"))

print(f"Loading embedding model: {EMBEDDING_MODEL_NAME} ...")
embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)


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
        timeout=OS_REQUEST_TIMEOUT,
    )


def embed_texts(texts: List[str]) -> List[List[float]]:
    vecs = embed_model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vecs.tolist()


def normalize_content(raw) -> str:
    """Convert content to a plain string — handles both str and table dicts."""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        parts = []
        headers = raw.get("headers")
        if headers and isinstance(headers, list):
            parts.append(" | ".join(str(h) for h in headers))
        rows = raw.get("rows")
        if rows and isinstance(rows, list):
            for row in rows:
                if isinstance(row, list):
                    parts.append(" | ".join(str(cell) for cell in row))
                else:
                    parts.append(str(row))
        return "\n".join(parts) if parts else json.dumps(raw)
    return str(raw) if raw else ""


def iter_chunks(data_dir: str) -> Iterator[Dict[str, Any]]:
    """Yield one dict per chunk from all JSON files under data_dir."""
    root = Path(data_dir)
    if not root.is_dir():
        return
    for path in sorted(root.glob("*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                chunks = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Skip {path}: {e}", file=sys.stderr)
            continue
        if not isinstance(chunks, list):
            continue
        for chunk in chunks:
            chunk["source_file"] = path.name
            chunk["content"] = normalize_content(chunk.get("content", ""))
            yield chunk


def main():
    if not Path(CORE_DATA_DIR).is_dir():
        print(f"ERROR: Core data directory not found: {CORE_DATA_DIR}")
        print(f"       Run 'python -m AWS.data.prepare_data' first to organize the data.")
        sys.exit(1)

    client = os_client()
    try:
        info = client.info()
        print(f"Connected to OpenSearch {info['version']['number']} at {OPENSEARCH_HOST}")
    except Exception as e:
        print(f"ERROR: Cannot connect to OpenSearch at {OPENSEARCH_HOST}: {e}")
        sys.exit(1)

    actions: List[Dict[str, Any]] = []
    batch_texts: List[str] = []
    batch_docs: List[Dict[str, Any]] = []
    total = 0
    skipped = 0

    for chunk in tqdm(iter_chunks(CORE_DATA_DIR), desc="Embed + index (core)"):
        chunk_id = chunk.get("chunk_id")
        content = chunk.get("content", "").strip()

        if not chunk_id:
            skipped += 1
            continue
        if not content or len(content) < 10:
            skipped += 1
            continue

        doc = {
            "chunk_id": chunk_id,
            "year": chunk.get("year"),
            "wave": chunk.get("wave"),
            "doc_type": chunk.get("doc_type"),
            "section_number": chunk.get("section_number"),
            "heading_name": chunk.get("heading_name"),
            "page_range": chunk.get("page_range"),
            "content_type": chunk.get("content_type"),
            "source_file": chunk.get("source_file"),
            "content": content,
        }
        batch_docs.append(doc)
        batch_texts.append(content)
        total += 1

        if len(batch_texts) >= BATCH_SIZE:
            vecs = embed_texts(batch_texts)
            for d, v in zip(batch_docs, vecs):
                d["embedding"] = v
                actions.append({"_op_type": "index", "_index": OS_INDEX, "_id": d["chunk_id"], "_source": d})
            batch_docs.clear()
            batch_texts.clear()

            if len(actions) >= OS_BULK_FLUSH:
                bulk(client, actions, request_timeout=OS_REQUEST_TIMEOUT)
                actions = []

    # Flush remaining
    if batch_texts:
        vecs = embed_texts(batch_texts)
        for d, v in zip(batch_docs, vecs):
            d["embedding"] = v
            actions.append({"_op_type": "index", "_index": OS_INDEX, "_id": d["chunk_id"], "_source": d})

    if actions:
        bulk(client, actions, request_timeout=OS_REQUEST_TIMEOUT)

    print(f"\nDone — {total} core chunks indexed, {skipped} skipped.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
