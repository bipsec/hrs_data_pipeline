from fastapi import APIRouter, HTTPException, Query, Path as PathParam
from typing import Any, Dict, List, Optional
from ...dependencies import get_mongodb_client
from ...models import CodebookSummary
from ....models.cores import (
    get_core_period,
    get_wave_number,
    HRS_LEGACY_YEARS,
    HRS_MODERN_YEARS,
)
from ...models import VariableSummary, SearchResponse, SectionResponse, VariableDetail, VariableTemporalResponse
from ....models.cores import get_year_prefix, construct_variable_name


router = APIRouter(prefix="/api/v1/hrs/ahead-exit", tags=["Codebooks"])

@router.get("/codebooks", response_model=List[CodebookSummary])
async def get_codebooks(
    year: Optional[int] = Query(None, description="Filter by year"),
    source: Optional[str] = Query(None, description="Filter by source (e.g., ahead_exit_codebook)"),
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
    source: str = Query("ahead_exit_codebook", description="Source name"),
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
    

@router.get("/search", response_model=SearchResponse)
async def search_variables(
    q: str = Query(..., description="Search query (searches variable names and descriptions)"),
    year: Optional[int] = Query(None, description="Filter by year"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
):
    """Search for variables by name or description."""
    with get_mongodb_client() as client:
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
    
@router.get("/sections", response_model=List[SectionResponse])
async def get_sections(
    year: int = Query(..., description="Year of the codebook"),
    source: str = Query("ahead_exit_codebook", description="Source name"),
):
    """Get all sections for a codebook."""
    with get_mongodb_client() as client:
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
    source: str = Query("ahead_exit_codebook", description="Source name"),
):
    """Get a specific section by code."""
    with get_mongodb_client() as client:
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
    

@router.get("/variables", response_model=List[VariableSummary])
async def get_variables(
    year: Optional[int] = Query(None, description="Filter by year"),
    source: Optional[str] = Query(None, description="Filter by source"),
    section: Optional[str] = Query(None, description="Filter by section code"),
    level: Optional[str] = Query(None, description="Filter by level"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
):
    """Get list of variables with optional filters."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        query: Dict[str, Any] = {}
        if year:
            query["year"] = year
        if source:
            query["source"] = source
        codebook = collection.find_one(query)
        if not codebook:
            raise HTTPException(status_code=404, detail="Codebook not found")
        variables = codebook.get("variables", [])
        filtered_vars = []
        for var in variables:
            if section and var.get("section") != section:
                continue
            if level and var.get("level") != level:
                continue
            filtered_vars.append(var)
        filtered_vars = filtered_vars[:limit]
        return [
            VariableSummary(
                name=var["name"], year=var["year"], section=var["section"],
                level=var["level"], description=var["description"], type=var["type"],
            )
            for var in filtered_vars
        ]


@router.get("/variables/{variable_name}", response_model=VariableDetail)
async def get_variable(
    variable_name: str = PathParam(..., description="Variable name"),
    year: int = Query(..., description="Year of the codebook"),
    source: str = Query("ahead_exit_codebook", description="Source name"),
):
    """Get detailed information about a specific variable."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        codebook = collection.find_one({"year": year, "source": source})
        if not codebook:
            raise HTTPException(status_code=404, detail=f"Codebook not found for year {year} and source {source}")
        variables = codebook.get("variables", [])
        variable = next((v for v in variables if v["name"] == variable_name), None)
        if not variable:
            raise HTTPException(status_code=404, detail=f"Variable '{variable_name}' not found in {year} {source}")
        return VariableDetail(**variable)


@router.get("/variables/base/{base_name}", response_model=List[VariableSummary])
async def get_variable_by_base_name(
    base_name: str = PathParam(..., description="Base variable name (e.g., 'SUBHH')"),
    years: Optional[str] = Query(None, description="Comma-separated list of years to include"),
    source: str = Query("ahead_exit_codebook", description="Source name"),
):
    """Get all instances of a variable across years by base name."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        year_list = None
        if years:
            try:
                year_list = [int(y.strip()) for y in years.split(",")]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid years format. Use comma-separated integers.")
        query: Dict[str, Any] = {"source": source}
        if year_list:
            query["year"] = {"$in": year_list}
        codebooks = list(collection.find(query))
        if not codebooks:
            raise HTTPException(status_code=404, detail=f"No codebooks found for source {source}")
        results = []
        for codebook in codebooks:
            year = codebook["year"]
            var_name = construct_variable_name(base_name, year)
            variables = codebook.get("variables", [])
            variable = next((v for v in variables if v["name"] == var_name), None)
            if variable:
                results.append(VariableSummary(
                    name=variable["name"], year=year,
                    section=variable.get("section", ""), level=variable.get("level", ""),
                    description=variable.get("description", ""), type=variable.get("type", ""),
                ))
        if not results:
            raise HTTPException(status_code=404, detail=f"Variable with base name '{base_name}' not found")
        return results


@router.get("/variables/base/{base_name}/temporal", response_model=VariableTemporalResponse)
async def get_variable_temporal_mapping(
    base_name: str = PathParam(..., description="Base variable name"),
    source: str = Query("ahead_exit_codebook", description="Source name"),
):
    """Get temporal mapping information for a variable across all years."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        codebooks = list(collection.find({"source": source}))
        if not codebooks:
            raise HTTPException(status_code=404, detail=f"No codebooks found for source {source}")
        years_present = []
        year_prefixes = {}
        for codebook in codebooks:
            year = codebook["year"]
            prefix = get_year_prefix(year)
            var_name = construct_variable_name(base_name, year)
            variables = codebook.get("variables", [])
            variable = next((v for v in variables if v["name"] == var_name), None)
            if variable:
                years_present.append(year)
                if prefix:
                    year_prefixes[year] = prefix
        if not years_present:
            raise HTTPException(status_code=404, detail=f"Variable with base name '{base_name}' not found in any year")
        return VariableTemporalResponse(
            base_name=base_name,
            years=sorted(years_present),
            year_prefixes=year_prefixes,
            first_year=min(years_present),
            last_year=max(years_present),
            consistent_metadata=True,
            consistent_values=True,
        )
