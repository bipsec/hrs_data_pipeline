"""Hybrid (BM25 + KNN) search over HRS Core data description chunks in OpenSearch.

Method 1: Combined BM25 + KNN query
Method 2 (fallback): Separate BM25 + KNN + manual RRF fusion
Embeddings via sentence-transformers (BAAI/bge-large-en-v1.5).
"""
import argparse
import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import numpy as np
from dotenv import load_dotenv
from opensearchpy import OpenSearch
from sentence_transformers import SentenceTransformer

from logger import setup_logger, log_json

load_dotenv()

OPENSEARCH_HOST = os.getenv("OPENSEARCH_HOST", "http://localhost:9200")
OPENSEARCH_USER = os.getenv("OPENSEARCH_USER", "admin")
OPENSEARCH_PASSWORD = os.getenv("OPENSEARCH_PASSWORD", "admin")
OS_INDEX = os.getenv("OS_INDEX", "hrs_core_data_desc")

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL", "BAAI/bge-large-en-v1.5")
EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "1024"))

TOP_K = int(os.getenv("HYBRID_TOP_K", "20"))
BM25_K = 80
KNN_K = 120
RRF_RANK_CONSTANT = 60

logger = setup_logger()
embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)


def _build_os_client() -> OpenSearch:
    parsed = urlparse(OPENSEARCH_HOST)
    return OpenSearch(
        hosts=[{"host": parsed.hostname or "localhost", "port": parsed.port or 9200}],
        http_auth=(OPENSEARCH_USER, OPENSEARCH_PASSWORD),
        use_ssl=parsed.scheme == "https",
        verify_certs=False,
        timeout=120,
    )


os_client = _build_os_client()


def embed_query(query: str) -> List[float]:
    return embed_model.encode(query, normalize_embeddings=True).tolist()


def build_filter(filters: Optional[Dict[str, Any]]) -> List[Dict]:
    if not filters:
        return []
    out = []
    for k, v in filters.items():
        if v is None:
            continue
        if isinstance(v, list):
            if v:
                out.append({"terms": {k: v}})
        else:
            out.append({"term": {k: v}})
    return out


def _hit_to_result(rank: int, h: Dict, score: float) -> Dict[str, Any]:
    src = h.get("_source") or {}
    content = src.get("content", "")
    content_preview = content[:300] + "..." if len(content) > 300 else content
    return {
        "rank": rank,
        "data_source": "core",
        "index": OS_INDEX,
        "chunk_id": src.get("chunk_id"),
        "year": src.get("year"),
        "wave": src.get("wave"),
        "doc_type": src.get("doc_type"),
        "section_number": src.get("section_number"),
        "heading_name": src.get("heading_name"),
        "page_range": src.get("page_range"),
        "_score": round(score, 6),
        "content_preview": content_preview,
    }


def hybrid_search_logged(query: str, filters: Optional[Dict[str, Any]] = None):
    logger.info("===== HRS CORE HYBRID SEARCH (data_desc) START =====")
    log_json(logger, "Query", {"query": query, "filters": filters})

    qvec = embed_query(query)
    vec_norm = float(np.linalg.norm(qvec))
    log_json(logger, "Embedding", {"model": EMBEDDING_MODEL_NAME, "dim": len(qvec), "l2_norm": round(vec_norm, 4)})

    es_filter = build_filter(filters)

    # Method 1: Combined BM25 + KNN
    try:
        body = {
            "size": TOP_K,
            "query": {
                "bool": {
                    "must": [{"multi_match": {"query": query, "fields": ["heading_name^8", "content"]}}],
                    "filter": es_filter,
                }
            },
            "knn": {"embedding": {"vector": qvec, "k": KNN_K}},
        }
        if es_filter:
            body["knn"]["embedding"]["filter"] = {"bool": {"filter": es_filter}}
        resp = os_client.search(index=OS_INDEX, body=body)
        if resp.get("hits", {}).get("hits"):
            hits = resp["hits"]["hits"]
            results = [_hit_to_result(rank, h, h["_score"]) for rank, h in enumerate(hits, start=1)]
            log_json(logger, "Final Ranked Results", results)
            logger.info("===== HRS CORE HYBRID SEARCH END =====\n")
            return results
    except Exception as e:
        logger.warning(f"Combined query failed ({e}), falling back to separate searches")

    # Method 2: Separate BM25 + KNN + RRF
    bm25_resp = os_client.search(index=OS_INDEX, body={
        "size": BM25_K,
        "query": {"bool": {"must": [{"multi_match": {"query": query, "fields": ["heading_name^8", "content"]}}], "filter": es_filter}},
    })
    bm25_ids = [h["_id"] for h in bm25_resp["hits"]["hits"]]

    knn_body: Dict[str, Any] = {"size": KNN_K, "query": {"knn": {"embedding": {"vector": qvec, "k": KNN_K}}}}
    if es_filter:
        knn_body["query"]["knn"]["embedding"]["filter"] = {"bool": {"filter": es_filter}}
    knn_resp = os_client.search(index=OS_INDEX, body=knn_body)
    knn_ids = [h["_id"] for h in knn_resp["hits"]["hits"]]

    scores: Dict[str, float] = {}
    for rank_list in [bm25_ids, knn_ids]:
        for rank, did in enumerate(rank_list, start=1):
            if did not in scores:
                scores[did] = 0.0
            scores[did] += 1.0 / (RRF_RANK_CONSTANT + rank)
    fused = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:TOP_K]
    fused_ids = [did for did, _ in fused]

    if not fused_ids:
        logger.info("===== HRS CORE HYBRID SEARCH END (no results) =====\n")
        return []

    mget_resp = os_client.mget(body={"docs": [{"_index": OS_INDEX, "_id": did} for did in fused_ids]})
    docs_by_id = {d["_id"]: d for d in mget_resp["docs"] if d.get("found")}

    results = []
    for rank, doc_id in enumerate(fused_ids, start=1):
        if doc_id in docs_by_id:
            doc = docs_by_id[doc_id]
            score = next((s for fid, s in fused if fid == doc_id), 0.0)
            results.append(_hit_to_result(rank, {"_source": doc.get("_source", {}), "_score": score}, score))

    log_json(logger, "Final Ranked Results", results)
    logger.info("===== HRS CORE HYBRID SEARCH END =====\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hybrid search over HRS Core data descriptions (OpenSearch)")
    parser.add_argument("query", nargs="?", default="sample interviewed respondents", help="Search query")
    parser.add_argument("--year", type=int, default=None, help="Filter by year")
    args = parser.parse_args()
    filters = {"year": args.year} if args.year else None
    hybrid_search_logged(args.query, filters=filters)
