"""Shared logic for HRS (core, exit, post_exit) embedding scripts — local sentence-transformers.

Reads data description chunks from AWS/data/{core,exit,post_exit}/*.json,
embeds via BAAI/bge-large-en-v1.5, and writes records.jsonl, doc_ids.txt,
embedding shards (.npy), and manifest.
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterator, List

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

load_dotenv()

_SCRIPT_DIR = Path(__file__).resolve().parent
_AWS_DIR = _SCRIPT_DIR.parent

CONFIG = {
    "core": {"data_subdir": "data/core", "out_subdir": "embeddings/core"},
    "exit": {"data_subdir": "data/exit", "out_subdir": "embeddings/exit"},
    "post_exit": {"data_subdir": "data/post_exit", "out_subdir": "embeddings/post_exit"},
}

# ---- Embedding config ----
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))
BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", "64"))
SHARD_SIZE = int(os.getenv("EMBED_SHARD_SIZE", "50000"))

print(f"Loading embedding model: {EMBEDDING_MODEL_NAME} ...")
embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)


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


def iter_chunks(data_dir: Path) -> Iterator[Dict[str, Any]]:
    """Yield one dict per chunk from all JSON files under data_dir."""
    if not data_dir.is_dir():
        return
    for path in sorted(data_dir.glob("*.json")):
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


def embed_texts(texts: List[str]) -> List[List[float]]:
    vecs = embed_model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return vecs.tolist()


def save_shard(out_dir: Path, shard_idx: int, vecs: List[List[float]]) -> Path:
    arr = np.array(vecs, dtype=np.float32)
    shard_path = out_dir / f"embeddings_shard_{shard_idx:04d}.npy"
    np.save(shard_path, arr)
    return shard_path


def run(source: str) -> None:
    if source not in CONFIG:
        raise ValueError(f"source must be one of: {list(CONFIG.keys())}")

    cfg = CONFIG[source]
    env_key = {"core": "CORE_DATA_DIR", "exit": "EXIT_DATA_DIR", "post_exit": "POST_EXIT_DATA_DIR"}[source]
    data_dir = Path(os.getenv(env_key, str(_AWS_DIR / cfg["data_subdir"])))
    out_dir = Path(os.getenv("OUT_DIR", str(_AWS_DIR / "data" / cfg["out_subdir"])))

    out_dir.mkdir(parents=True, exist_ok=True)
    records_path = out_dir / "records.jsonl"
    ids_path = out_dir / "doc_ids.txt"
    manifest_path = out_dir / "embeddings_manifest.json"

    rec_out = open(records_path, "w", encoding="utf-8")
    id_out = open(ids_path, "w", encoding="utf-8")

    total = 0
    skipped = 0
    batch_texts: List[str] = []
    shard_idx = 0
    shard_vecs: List[List[float]] = []
    shard_files: List[Dict[str, Any]] = []

    docs_list = list(iter_chunks(data_dir))
    if not docs_list:
        print(f"No chunks found under {data_dir}")
        print(f"Run 'python -m AWS.data.prepare_data' first.")
        rec_out.close()
        id_out.close()
        return

    for chunk in tqdm(docs_list, desc=f"Embed {source}"):
        chunk_id = chunk.get("chunk_id")
        content = chunk.get("content", "").strip()

        if not chunk_id:
            skipped += 1
            continue
        if not content or len(content) < 10:
            skipped += 1
            continue

        out_doc = {
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
        rec_out.write(json.dumps(out_doc, ensure_ascii=False) + "\n")
        id_out.write(chunk_id + "\n")
        batch_texts.append(content)
        total += 1

        if len(batch_texts) >= BATCH_SIZE:
            vecs = embed_texts(batch_texts)
            shard_vecs.extend(vecs)
            batch_texts.clear()
        if len(shard_vecs) >= SHARD_SIZE:
            shard_path = save_shard(out_dir, shard_idx, shard_vecs)
            shard_files.append({"shard_index": shard_idx, "path": str(shard_path), "count": len(shard_vecs), "dims": EMBEDDING_DIM})
            shard_idx += 1
            shard_vecs = []

    if batch_texts:
        vecs = embed_texts(batch_texts)
        shard_vecs.extend(vecs)
    if shard_vecs:
        shard_path = save_shard(out_dir, shard_idx, shard_vecs)
        shard_files.append({"shard_index": shard_idx, "path": str(shard_path), "count": len(shard_vecs), "dims": EMBEDDING_DIM})

    rec_out.close()
    id_out.close()

    with open(manifest_path, "w", encoding="utf-8") as mf:
        json.dump({
            "source": source,
            "embedding_model": EMBEDDING_MODEL_NAME,
            "embedding_dim": EMBEDDING_DIM,
            "batch_size": BATCH_SIZE,
            "shard_size": SHARD_SIZE,
            "shards": shard_files,
        }, mf, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"HRS {source.upper()} Embeddings Complete (sentence-transformers)")
    print(f"{'='*60}")
    print(f"Model: {EMBEDDING_MODEL_NAME}")
    print(f"Dimensions: {EMBEDDING_DIM}")
    print(f"Total: {total}  Skipped: {skipped}")
    print(f"Records: {records_path}")
    print(f"Shards: {len(shard_files)}")
