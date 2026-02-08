"""Codebook endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path as PathParam

from ...dependencies import get_mongodb_client
from ...models import CodebookSummary
from ....models.cores import (
    get_core_period,
    get_wave_number,
    HRS_LEGACY_YEARS,
    HRS_MODERN_YEARS,
)

router = APIRouter(tags=["Codebooks"])


@router.get("/codebooks", response_model=List[CodebookSummary])
async def get_codebooks(
    year: Optional[int] = Query(None, description="Filter by year"),
    source: Optional[str] = Query(None, description="Filter by source (e.g., hrs_core_codebook)"),
    core_period: Optional[str] = Query(None, description="Filter by core period: 'legacy' (1992-2004) or 'modern' (2008-2022)"),
):
    """Get list of codebooks with optional filters."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        query: Dict[str, Any] = {}
        if year:
            query["year"] = year
        elif core_period:
            if core_period.lower() == "legacy":
                query["year"] = {"$in": sorted(HRS_LEGACY_YEARS)}
            elif core_period.lower() == "modern":
                query["year"] = {"$in": sorted(HRS_MODERN_YEARS)}
        if source:
            query["source"] = source
        codebooks = list(collection.find(query, {
            "source": 1, "year": 1, "release_type": 1, "core_period": 1,
            "total_variables": 1, "total_sections": 1, "levels": 1,
        }))
        if not codebooks:
            raise HTTPException(status_code=404, detail="No codebooks found")
        return [
            CodebookSummary(
                source=cb["source"],
                year=cb["year"],
                wave=cb.get("wave") or get_wave_number(cb["year"]),
                release_type=cb.get("release_type"),
                core_period=cb.get("core_period") or (get_core_period(cb["year"]).value if cb.get("year") else None),
                total_variables=cb["total_variables"],
                total_sections=cb["total_sections"],
                levels=list(cb.get("levels", [])),
            )
            for cb in codebooks
        ]


@router.get("/codebooks/{year}", response_model=CodebookSummary)
async def get_codebook_by_year(
    year: int = PathParam(..., description="Year of the codebook"),
    source: str = Query("hrs_core_codebook", description="Source name"),
):
    """Get a specific codebook by year and source."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        codebook = collection.find_one({"year": year, "source": source})
        if not codebook:
            raise HTTPException(status_code=404, detail=f"Codebook not found for year {year} and source {source}")
        return CodebookSummary(
            source=codebook["source"],
            year=codebook["year"],
            wave=codebook.get("wave") or get_wave_number(codebook["year"]),
            release_type=codebook.get("release_type"),
            core_period=codebook.get("core_period") or get_core_period(codebook["year"]).value,
            total_variables=codebook["total_variables"],
            total_sections=codebook["total_sections"],
            levels=list(codebook.get("levels", [])),
        )
