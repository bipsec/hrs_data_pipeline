"""Section endpoints."""

from typing import List
from fastapi import APIRouter, HTTPException, Query, Path as PathParam

from ...dependencies import get_mongodb_client
from ...models import SectionResponse

router = APIRouter(tags=["Sections"])


@router.get("/sections", response_model=List[SectionResponse])
async def get_sections(
    year: int = Query(..., description="Year of the codebook"),
    source: str = Query("hrs_core_codebook", description="Source name"),
):
    """Get all sections for a codebook."""
    client = get_mongodb_client()
    collection = client.get_collection("codebooks")
    codebook = collection.find_one({"year": year, "source": source})
    if not codebook:
        raise HTTPException(status_code=404, detail=f"Codebook not found for year {year} and source {source}")
    sections = codebook.get("sections", [])
    return [
        SectionResponse(
            code=sec["code"], name=sec["name"], level=sec["level"],
            year=sec["year"], variable_count=sec["variable_count"], variables=sec["variables"],
        )
        for sec in sections
    ]


@router.get("/sections/{section_code}", response_model=SectionResponse)
async def get_section(
    section_code: str = PathParam(..., description="Section code (e.g., 'PR', 'A')"),
    year: int = Query(..., description="Year of the codebook"),
    source: str = Query("hrs_core_codebook", description="Source name"),
):
    """Get a specific section by code."""
    client = get_mongodb_client()
    sections_collection = client.get_collection("sections")
    section_doc = sections_collection.find_one({
        "year": year, "source": source, "section.code": section_code,
    })
    if section_doc:
        section = section_doc.get("section", {})
        return SectionResponse(
            code=section["code"], name=section["name"], level=section["level"],
            year=section["year"], variable_count=section["variable_count"], variables=section["variables"],
        )
    codebooks_collection = client.get_collection("codebooks")
    codebook = codebooks_collection.find_one({"year": year, "source": source})
    if not codebook:
        raise HTTPException(status_code=404, detail=f"Codebook not found for year {year} and source {source}")
    sections = codebook.get("sections", [])
    section = next((s for s in sections if s["code"] == section_code), None)
    if not section:
        raise HTTPException(status_code=404, detail=f"Section '{section_code}' not found in {year} {source}")
    return SectionResponse(
        code=section["code"], name=section["name"], level=section["level"],
        year=section["year"], variable_count=section["variable_count"], variables=section["variables"],
    )
