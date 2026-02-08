"""Exit codebook and variable endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path as PathParam

from ...dependencies import get_mongodb_client
from ...models import (
    EXIT_SOURCE,
    ExitCodebookSummary,
    ExitVariableSummary,
    ExitVariableDetail,
    ExitValueCodeResponse,
    ExitSectionResponse,
    ExitSearchResponse,
)

router = APIRouter(prefix="/exit", tags=["Exit"])


def _level_str(v: Any) -> str:
    return v if isinstance(v, str) else getattr(v, "value", str(v))


def _var_to_summary(var: Dict[str, Any], year: int) -> ExitVariableSummary:
    return ExitVariableSummary(
        name=var.get("name", ""),
        year=year,
        section=var.get("section", ""),
        level=_level_str(var.get("level", "")),
        description=var.get("description", ""),
        type=_level_str(var.get("type", "")),
    )


def _var_to_detail(var: Dict[str, Any]) -> ExitVariableDetail:
    vc = var.get("value_codes") or []
    return ExitVariableDetail(
        name=var.get("name", ""),
        year=var.get("year", 0),
        section=var.get("section", ""),
        level=_level_str(var.get("level", "")),
        description=var.get("description", ""),
        type=_level_str(var.get("type", "")),
        width=var.get("width", 0),
        decimals=var.get("decimals", 0),
        value_codes=[
            ExitValueCodeResponse(
                code=c.get("code", ""),
                frequency=c.get("frequency"),
                label=c.get("label"),
                is_missing=c.get("is_missing", False),
            )
            for c in vc
        ],
        has_value_codes=var.get("has_value_codes", len(vc) > 0),
        notes=var.get("notes"),
    )


@router.get("/codebooks", response_model=List[ExitCodebookSummary])
async def get_exit_codebooks(
    year: Optional[int] = Query(None, description="Filter by year"),
    source: str = Query(EXIT_SOURCE, description="Source (default hrs_exit_codebook)"),
):
    """List exit codebooks, optionally filtered by year."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        query: Dict[str, Any] = {"source": source}
        if year is not None:
            query["year"] = year
        codebooks = list(collection.find(query, {
            "source": 1, "year": 1, "release_type": 1,
            "total_variables": 1, "total_sections": 1, "levels": 1,
        }))
        if not codebooks:
            return []
        return [
            ExitCodebookSummary(
                source=cb.get("source", EXIT_SOURCE),
                year=cb["year"],
                release_type=cb.get("release_type"),
                total_variables=cb.get("total_variables", 0),
                total_sections=cb.get("total_sections", 0),
                levels=list(cb.get("levels", [])),
            )
            for cb in codebooks
        ]


@router.get("/codebooks/{year}", response_model=ExitCodebookSummary)
async def get_exit_codebook_by_year(
    year: int = PathParam(..., description="Exit codebook year"),
    source: str = Query(EXIT_SOURCE, description="Source name"),
):
    """Get a single exit codebook by year."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        codebook = collection.find_one({"year": year, "source": source})
        if not codebook:
            raise HTTPException(
                status_code=404,
                detail=f"Exit codebook not found for year {year} and source {source}",
            )
        return ExitCodebookSummary(
            source=codebook.get("source", EXIT_SOURCE),
            year=codebook["year"],
            release_type=codebook.get("release_type"),
            total_variables=codebook.get("total_variables", 0),
            total_sections=codebook.get("total_sections", 0),
            levels=list(codebook.get("levels", [])),
        )


@router.get("/variables", response_model=List[ExitVariableSummary])
async def get_exit_variables(
    year: Optional[int] = Query(None, description="Filter by year"),
    source: str = Query(EXIT_SOURCE, description="Source name"),
    section: Optional[str] = Query(None, description="Filter by section code"),
    level: Optional[str] = Query(None, description="Filter by level"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
):
    """List exit variables with optional filters."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        query: Dict[str, Any] = {"source": source}
        if year is not None:
            query["year"] = year
        codebook = collection.find_one(query)
        if not codebook:
            raise HTTPException(status_code=404, detail="Exit codebook not found")
        variables = codebook.get("variables", [])
        cb_year = codebook.get("year", 0)
        out = []
        for var in variables:
            if section and var.get("section") != section:
                continue
            if level and _level_str(var.get("level", "")) != level:
                continue
            out.append(_var_to_summary(var, cb_year))
        return out[:limit]


@router.get("/variables/{variable_name}", response_model=ExitVariableDetail)
async def get_exit_variable(
    variable_name: str = PathParam(..., description="Exit variable name"),
    year: int = Query(..., description="Codebook year"),
    source: str = Query(EXIT_SOURCE, description="Source name"),
):
    """Get full details for one exit variable."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        codebook = collection.find_one({"year": year, "source": source})
        if not codebook:
            raise HTTPException(
                status_code=404,
                detail=f"Exit codebook not found for year {year} and source {source}",
            )
        variables = codebook.get("variables", [])
        variable = next((v for v in variables if v.get("name") == variable_name), None)
        if not variable:
            raise HTTPException(
                status_code=404,
                detail=f"Exit variable '{variable_name}' not found in {year} {source}",
            )
        variable["year"] = year
        return _var_to_detail(variable)


@router.get("/sections", response_model=List[ExitSectionResponse])
async def get_exit_sections(
    year: int = Query(..., description="Codebook year"),
    source: str = Query(EXIT_SOURCE, description="Source name"),
):
    """Get all sections for an exit codebook."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        codebook = collection.find_one({"year": year, "source": source})
        if not codebook:
            raise HTTPException(
                status_code=404,
                detail=f"Exit codebook not found for year {year} and source {source}",
            )
        sections = codebook.get("sections", [])
        return [
            ExitSectionResponse(
                code=sec.get("code", ""),
                name=sec.get("name", ""),
                level=_level_str(sec.get("level", "")),
                year=sec.get("year", year),
                variable_count=sec.get("variable_count", 0),
                variables=sec.get("variables", []),
            )
            for sec in sections
        ]


@router.get("/sections/{section_code}", response_model=ExitSectionResponse)
async def get_exit_section(
    section_code: str = PathParam(..., description="Section code (e.g. A, PR)"),
    year: int = Query(..., description="Codebook year"),
    source: str = Query(EXIT_SOURCE, description="Source name"),
):
    """Get one exit section by code."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        codebook = collection.find_one({"year": year, "source": source})
        if not codebook:
            raise HTTPException(
                status_code=404,
                detail=f"Exit codebook not found for year {year} and source {source}",
            )
        sections = codebook.get("sections", [])
        section = next((s for s in sections if s.get("code") == section_code), None)
        if not section:
            raise HTTPException(
                status_code=404,
                detail=f"Exit section '{section_code}' not found in {year} {source}",
            )
        return ExitSectionResponse(
            code=section.get("code", ""),
            name=section.get("name", ""),
            level=_level_str(section.get("level", "")),
            year=section.get("year", year),
            variable_count=section.get("variable_count", 0),
            variables=section.get("variables", []),
        )


@router.get("/search", response_model=ExitSearchResponse)
async def search_exit_variables(
    q: str = Query(..., description="Search query (name or description)"),
    year: Optional[int] = Query(None, description="Filter by year"),
    source: str = Query(EXIT_SOURCE, description="Source name"),
    limit: int = Query(50, ge=1, le=500, description="Max results"),
):
    """Search exit variables by name or description."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        query: Dict[str, Any] = {"source": source}
        if year is not None:
            query["year"] = year
        codebooks = list(collection.find(query))
        if not codebooks:
            return ExitSearchResponse(query=q, total=0, results=[], limit=limit)
        q_lower = q.lower()
        results = []
        for codebook in codebooks:
            cb_year = codebook.get("year", 0)
            for var in codebook.get("variables", []):
                if q_lower in var.get("name", "").lower() or q_lower in var.get("description", "").lower():
                    results.append(_var_to_summary(var, cb_year))
        total = len(results)
        return ExitSearchResponse(query=q, total=total, results=results[:limit], limit=limit)
