"""General endpoints: root, years, stats, waves."""

from typing import List
from pathlib import Path
from fastapi import APIRouter, HTTPException, Path as PathParam
from fastapi.responses import FileResponse

from ...dependencies import get_mongodb_client
from ...models import YearsResponse, WaveInfo
from ....models.cores import (
    HRS_YEARS,
    HRS_LEGACY_YEARS,
    HRS_MODERN_YEARS,
    YEAR_PREFIX_MAP,
    HRS_SECTION_CODES,
    get_wave_number,
    get_year_prefix,
    get_year_from_wave,
)

router = APIRouter(tags=["General"])

# Static path: from api/routes/shared/general.py -> api/static
static_path = Path(__file__).resolve().parent.parent.parent / "static"


@router.get("/")
async def root():
    """Root endpoint - redirects to UI or returns API info."""
    ui_path = static_path / "index.html"
    if ui_path.exists():
        return FileResponse(str(ui_path))
    return {
        "message": "HRS Data Pipeline API",
        "version": "1.0.0",
        "ui": "/static/index.html",
        "endpoints": {
            "codebooks": "/codebooks",
            "variables": "/variables",
            "sections": "/sections",
            "search": "/search",
            "years": "/years",
            "exit": "/exit",
        },
    }


@router.get("/years", response_model=YearsResponse)
async def get_years():
    """Get list of available years and sources."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        years = sorted(collection.distinct("year"))
        sources = sorted(collection.distinct("source"))
        return YearsResponse(
            years=years,
            sources=sources,
            hrs_years=sorted(list(HRS_YEARS)),
            hrs_legacy_years=sorted(list(HRS_LEGACY_YEARS)),
            hrs_modern_years=sorted(list(HRS_MODERN_YEARS)),
            year_prefix_map=dict(YEAR_PREFIX_MAP),
        )


@router.get("/stats")
async def get_stats():
    """Get statistics about the database."""
    with get_mongodb_client() as client:
        codebooks_collection = client.get_collection("codebooks")
        sections_collection = client.get_collection("sections")
        index_collection = client.get_collection("variables_index")
        total_codebooks = codebooks_collection.count_documents({})
        total_sections = sections_collection.count_documents({})
        total_indexes = index_collection.count_documents({})
        codebooks = list(codebooks_collection.find({}, {"total_variables": 1}))
        total_variables = sum(cb.get("total_variables", 0) for cb in codebooks)
        years = sorted(codebooks_collection.distinct("year"))
        year_range = f"{min(years)}-{max(years)}" if years else "N/A"
        return {
            "total_codebooks": total_codebooks,
            "total_sections": total_sections,
            "total_variables": total_variables,
            "total_indexes": total_indexes,
            "year_range": year_range,
            "years": years,
            "sources": sorted(codebooks_collection.distinct("source")),
            "hrs_years_supported": sorted(list(HRS_YEARS)),
            "section_codes": sorted(list(HRS_SECTION_CODES)),
        }


@router.get("/waves", response_model=List[WaveInfo])
async def get_waves():
    """Get information about all HRS waves (1-16)."""
    waves = []
    for year in sorted(HRS_YEARS):
        wave = get_wave_number(year)
        prefix = get_year_prefix(year)
        if wave:
            waves.append(WaveInfo(wave=wave, year=year, prefix=prefix or ""))
    return waves


@router.get("/waves/{wave}", response_model=WaveInfo)
async def get_wave_info(wave: int = PathParam(..., ge=1, le=16, description="Wave number (1-16)")):
    """Get information about a specific HRS wave."""
    year = get_year_from_wave(wave)
    if not year:
        raise HTTPException(status_code=404, detail=f"Wave {wave} not found")
    prefix = get_year_prefix(year)
    return WaveInfo(wave=wave, year=year, prefix=prefix or "")
