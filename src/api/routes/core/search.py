"""Search endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Query

from ...dependencies import get_mongodb_client
from ...models import VariableSummary, SearchResponse

router = APIRouter(tags=["Search"])


@router.get("/search", response_model=SearchResponse)
async def search_variables(
    q: str = Query(..., description="Search query (searches variable names and descriptions)"),
    year: Optional[int] = Query(None, description="Filter by year"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
):
    """Search for variables by name or description."""
    client = get_mongodb_client()
    index_collection = client.get_collection("variables_index")
    query: Dict[str, Any] = {}
    if year:
        query["year"] = year
    if source:
        query["source"] = source
    index_docs = list(index_collection.find(query))
    if not index_docs:
        codebooks_collection = client.get_collection("codebooks")
        codebook_query: Dict[str, Any] = {}
        if year:
            codebook_query["year"] = year
        if source:
            codebook_query["source"] = source
        codebooks = list(codebooks_collection.find(codebook_query))
        results = []
        query_lower = q.lower()
        for codebook in codebooks:
            variables = codebook.get("variables", [])
            for var in variables:
                name_match = query_lower in var.get("name", "").lower()
                desc_match = query_lower in var.get("description", "").lower()
                if name_match or desc_match:
                    results.append(VariableSummary(
                        name=var.get("name", ""), year=codebook.get("year", 0),
                        section=var.get("section", ""), level=var.get("level", ""),
                        description=var.get("description", ""), type=var.get("type", ""),
                    ))
        total = len(results)
        results = results[:limit]
        return SearchResponse(query=q, total=total, results=results, limit=limit)
    variables = []
    for index_doc in index_docs:
        variables.extend(index_doc.get("variables", []))
    query_lower = q.lower()
    results = []
    for var in variables:
        name_match = query_lower in var.get("name", "").lower()
        desc_match = query_lower in var.get("description", "").lower()
        if name_match or desc_match:
            results.append(VariableSummary(
                name=var.get("name", ""), year=var.get("year", 0),
                section=var.get("section", ""), level=var.get("level", ""),
                description=var.get("description", ""), type=var.get("type", ""),
            ))
    total = len(results)
    results = results[:limit]
    return SearchResponse(query=q, total=total, results=results, limit=limit)
