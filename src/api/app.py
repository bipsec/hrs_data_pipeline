"""FastAPI application for HRS data pipeline API."""

from fastapi import FastAPI, HTTPException, Query, Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from pathlib import Path

from ..database.mongodb_client import MongoDBClient
from ..models.cores import (
    Variable, ValueCode, Section, Codebook, VariableLevel, VariableType,
    extract_base_name, construct_variable_name, get_year_prefix, get_year_from_prefix,
    get_wave_number, get_year_from_wave, YEAR_PREFIX_MAP, HRS_YEARS, HRS_SECTION_CODES
)

app = FastAPI(
    title="HRS Data Pipeline API",
    description="API for querying HRS (Health and Retirement Study) codebook data",
    version="1.0.0"
)

# Mount static files for UI
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Response models
class VariableSummary(BaseModel):
    """Summary of a variable for search results."""
    name: str
    year: int
    section: str
    level: str
    description: str
    type: str


class VariableDetail(Variable):
    """Full variable details."""
    pass


class SectionResponse(BaseModel):
    """Section response model."""
    code: str
    name: str
    level: str
    year: int
    variable_count: int
    variables: List[str]


class CodebookSummary(BaseModel):
    """Codebook summary response."""
    source: str
    year: int
    wave: Optional[int] = None
    release_type: Optional[str] = None
    total_variables: int
    total_sections: int
    levels: List[str]


class SearchResponse(BaseModel):
    """Search response model."""
    query: str
    total: int
    results: List[VariableSummary]
    limit: int


class YearsResponse(BaseModel):
    """Available years response."""
    years: List[int]
    sources: List[str]
    hrs_years: List[int] = Field(default_factory=lambda: sorted(list(HRS_YEARS)))
    year_prefix_map: Dict[int, str] = Field(default_factory=lambda: YEAR_PREFIX_MAP)


class VariableTemporalResponse(BaseModel):
    """Temporal mapping response for a variable."""
    base_name: str
    years: List[int]
    year_prefixes: Dict[int, str]
    first_year: Optional[int] = None
    last_year: Optional[int] = None
    consistent_metadata: bool = True
    consistent_values: bool = True


class WaveInfo(BaseModel):
    """Wave information response."""
    wave: int
    year: int
    prefix: str


def get_mongodb_client() -> MongoDBClient:
    """Get MongoDB client instance."""
    return MongoDBClient()


@app.get("/", tags=["General"])
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
            "years": "/years"
        }
    }


@app.get("/codebooks", response_model=List[CodebookSummary], tags=["Codebooks"])
async def get_codebooks(
    year: Optional[int] = Query(None, description="Filter by year"),
    source: Optional[str] = Query(None, description="Filter by source (e.g., hrs_core_codebook)")
):
    """Get list of codebooks with optional filters."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        
        query: Dict[str, Any] = {}
        if year:
            query["year"] = year
        if source:
            query["source"] = source
        
        codebooks = list(collection.find(query, {
            "source": 1,
            "year": 1,
            "release_type": 1,
            "total_variables": 1,
            "total_sections": 1,
            "levels": 1
        }))
        
        if not codebooks:
            raise HTTPException(status_code=404, detail="No codebooks found")
        
        return [
            CodebookSummary(
                source=cb["source"],
                year=cb["year"],
                wave=cb.get("wave") or get_wave_number(cb["year"]),
                release_type=cb.get("release_type"),
                total_variables=cb["total_variables"],
                total_sections=cb["total_sections"],
                levels=list(cb.get("levels", []))
            )
            for cb in codebooks
        ]


@app.get("/codebooks/{year}", response_model=CodebookSummary, tags=["Codebooks"])
async def get_codebook_by_year(
    year: int = PathParam(..., description="Year of the codebook"),
    source: str = Query("hrs_core_codebook", description="Source name")
):
    """Get a specific codebook by year and source."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        
        codebook = collection.find_one({
            "year": year,
            "source": source
        })
        
        if not codebook:
            raise HTTPException(
                status_code=404,
                detail=f"Codebook not found for year {year} and source {source}"
            )
        
        return CodebookSummary(
            source=codebook["source"],
            year=codebook["year"],
            wave=codebook.get("wave") or get_wave_number(codebook["year"]),
            release_type=codebook.get("release_type"),
            total_variables=codebook["total_variables"],
            total_sections=codebook["total_sections"],
            levels=list(codebook.get("levels", []))
        )


@app.get("/variables", response_model=List[VariableSummary], tags=["Variables"])
async def get_variables(
    year: Optional[int] = Query(None, description="Filter by year"),
    source: Optional[str] = Query(None, description="Filter by source"),
    section: Optional[str] = Query(None, description="Filter by section code"),
    level: Optional[str] = Query(None, description="Filter by level"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results")
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
        
        # Apply filters
        filtered_vars = []
        for var in variables:
            if section and var.get("section") != section:
                continue
            if level and var.get("level") != level:
                continue
            filtered_vars.append(var)
        
        # Limit results
        filtered_vars = filtered_vars[:limit]
        
        return [
            VariableSummary(
                name=var["name"],
                year=var["year"],
                section=var["section"],
                level=var["level"],
                description=var["description"],
                type=var["type"]
            )
            for var in filtered_vars
        ]


@app.get("/variables/{variable_name}", response_model=VariableDetail, tags=["Variables"])
async def get_variable(
    variable_name: str = PathParam(..., description="Variable name"),
    year: int = Query(..., description="Year of the codebook"),
    source: str = Query("hrs_core_codebook", description="Source name")
):
    """Get detailed information about a specific variable."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        
        codebook = collection.find_one({
            "year": year,
            "source": source
        })
        
        if not codebook:
            raise HTTPException(
                status_code=404,
                detail=f"Codebook not found for year {year} and source {source}"
            )
        
        # Find variable in codebook
        variables = codebook.get("variables", [])
        variable = next((v for v in variables if v["name"] == variable_name), None)
        
        if not variable:
            raise HTTPException(
                status_code=404,
                detail=f"Variable '{variable_name}' not found in {year} {source}"
            )
        
        return VariableDetail(**variable)


@app.get("/sections", response_model=List[SectionResponse], tags=["Sections"])
async def get_sections(
    year: int = Query(..., description="Year of the codebook"),
    source: str = Query("hrs_core_codebook", description="Source name")
):
    """Get all sections for a codebook."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        
        codebook = collection.find_one({
            "year": year,
            "source": source
        })
        
        if not codebook:
            raise HTTPException(
                status_code=404,
                detail=f"Codebook not found for year {year} and source {source}"
            )
        
        sections = codebook.get("sections", [])
        
        return [
            SectionResponse(
                code=sec["code"],
                name=sec["name"],
                level=sec["level"],
                year=sec["year"],
                variable_count=sec["variable_count"],
                variables=sec["variables"]
            )
            for sec in sections
        ]


@app.get("/sections/{section_code}", response_model=SectionResponse, tags=["Sections"])
async def get_section(
    section_code: str = PathParam(..., description="Section code (e.g., 'PR', 'A')"),
    year: int = Query(..., description="Year of the codebook"),
    source: str = Query("hrs_core_codebook", description="Source name")
):
    """Get a specific section by code."""
    with get_mongodb_client() as client:
        # Try sections collection first
        sections_collection = client.get_collection("sections")
        
        section_doc = sections_collection.find_one({
            "year": year,
            "source": source,
            "section.code": section_code
        })
        
        if section_doc:
            section = section_doc.get("section", {})
            return SectionResponse(
                code=section["code"],
                name=section["name"],
                level=section["level"],
                year=section["year"],
                variable_count=section["variable_count"],
                variables=section["variables"]
            )
        
        # Fallback to codebook collection
        codebooks_collection = client.get_collection("codebooks")
        codebook = codebooks_collection.find_one({
            "year": year,
            "source": source
        })
        
        if not codebook:
            raise HTTPException(
                status_code=404,
                detail=f"Codebook not found for year {year} and source {source}"
            )
        
        sections = codebook.get("sections", [])
        section = next((s for s in sections if s["code"] == section_code), None)
        
        if not section:
            raise HTTPException(
                status_code=404,
                detail=f"Section '{section_code}' not found in {year} {source}"
            )
        
        return SectionResponse(
            code=section["code"],
            name=section["name"],
            level=section["level"],
            year=section["year"],
            variable_count=section["variable_count"],
            variables=section["variables"]
        )


@app.get("/search", response_model=SearchResponse, tags=["Search"])
async def search_variables(
    q: str = Query(..., description="Search query (searches variable names and descriptions)"),
    year: Optional[int] = Query(None, description="Filter by year"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results")
):
    """Search for variables by name or description."""
    with get_mongodb_client() as client:
        # Use variables_index for faster search
        index_collection = client.get_collection("variables_index")
        
        query: Dict[str, Any] = {}
        if year:
            query["year"] = year
        if source:
            query["source"] = source
        
        # Search across all matching index documents
        index_docs = list(index_collection.find(query))
        
        if not index_docs:
            # If no index found, try searching in codebooks directly
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
                            name=var.get("name", ""),
                            year=codebook.get("year", 0),
                            section=var.get("section", ""),
                            level=var.get("level", ""),
                            description=var.get("description", ""),
                            type=var.get("type", "")
                        ))
            
            total = len(results)
            results = results[:limit]
            
            return SearchResponse(
                query=q,
                total=total,
                results=results,
                limit=limit
            )
        
        # Search in all matching index documents
        variables = []
        for index_doc in index_docs:
            variables.extend(index_doc.get("variables", []))
        
        # Search in variable names and descriptions
        query_lower = q.lower()
        results = []
        
        for var in variables:
            name_match = query_lower in var.get("name", "").lower()
            desc_match = query_lower in var.get("description", "").lower()
            
            if name_match or desc_match:
                results.append(VariableSummary(
                    name=var.get("name", ""),
                    year=var.get("year", 0),
                    section=var.get("section", ""),
                    level=var.get("level", ""),
                    description=var.get("description", ""),
                    type=var.get("type", "")
                ))
        
        # Limit results
        total = len(results)
        results = results[:limit]
        
        return SearchResponse(
            query=q,
            total=total,
            results=results,
            limit=limit
        )


@app.get("/years", response_model=YearsResponse, tags=["General"])
async def get_years():
    """Get list of available years and sources."""
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        
        # Get distinct years and sources
        years = sorted(collection.distinct("year"))
        sources = sorted(collection.distinct("source"))
        
        return YearsResponse(
            years=years,
            sources=sources,
            hrs_years=sorted(list(HRS_YEARS)),
            year_prefix_map=YEAR_PREFIX_MAP
        )


@app.get("/stats", tags=["General"])
async def get_stats():
    """Get statistics about the database."""
    with get_mongodb_client() as client:
        codebooks_collection = client.get_collection("codebooks")
        sections_collection = client.get_collection("sections")
        index_collection = client.get_collection("variables_index")
        
        total_codebooks = codebooks_collection.count_documents({})
        total_sections = sections_collection.count_documents({})
        total_indexes = index_collection.count_documents({})
        
        # Get total variables across all codebooks
        codebooks = list(codebooks_collection.find({}, {"total_variables": 1}))
        total_variables = sum(cb.get("total_variables", 0) for cb in codebooks)
        
        # Get year range
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
            "section_codes": sorted(list(HRS_SECTION_CODES))
        }


# ===== Cross-Year Variable Mapping Endpoints =====

@app.get("/variables/base/{base_name}", response_model=List[VariableSummary], tags=["Variables"])
async def get_variable_by_base_name(
    base_name: str = PathParam(..., description="Base variable name (e.g., 'SUBHH')"),
    years: Optional[str] = Query(None, description="Comma-separated list of years to include"),
    source: str = Query("hrs_core_codebook", description="Source name")
):
    """Get all instances of a variable across years by base name.
    
    This endpoint uses the base name (without year prefix) to find variables
    across multiple years. For example, 'SUBHH' will find RSUBHH (2020),
    QSUBHH (2018), PSUBHH (2016), etc.
    """
    with get_mongodb_client() as client:
        collection = client.get_collection("codebooks")
        
        # Parse years if provided
        year_list = None
        if years:
            try:
                year_list = [int(y.strip()) for y in years.split(",")]
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid years format. Use comma-separated integers.")
        
        # Query codebooks
        query: Dict[str, Any] = {"source": source}
        if year_list:
            query["year"] = {"$in": year_list}
        
        codebooks = list(collection.find(query))
        
        if not codebooks:
            raise HTTPException(status_code=404, detail=f"No codebooks found for source {source}")
        
        results = []
        for codebook in codebooks:
            year = codebook["year"]
            prefix = get_year_prefix(year)
            
            # Construct variable name for this year
            var_name = construct_variable_name(base_name, year)
            
            # Find variable in codebook
            variables = codebook.get("variables", [])
            variable = next((v for v in variables if v["name"] == var_name), None)
            
            if variable:
                results.append(VariableSummary(
                    name=variable["name"],
                    year=year,
                    section=variable.get("section", ""),
                    level=variable.get("level", ""),
                    description=variable.get("description", ""),
                    type=variable.get("type", "")
                ))
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Variable with base name '{base_name}' not found"
            )
        
        return results


@app.get("/variables/base/{base_name}/temporal", response_model=VariableTemporalResponse, tags=["Variables"])
async def get_variable_temporal_mapping(
    base_name: str = PathParam(..., description="Base variable name"),
    source: str = Query("hrs_core_codebook", description="Source name")
):
    """Get temporal mapping information for a variable across all years.
    
    Returns information about which years a variable appears in, what prefixes
    are used, and consistency information.
    """
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
            
            # Check if variable exists
            variables = codebook.get("variables", [])
            variable = next((v for v in variables if v["name"] == var_name), None)
            
            if variable:
                years_present.append(year)
                if prefix:
                    year_prefixes[year] = prefix
        
        if not years_present:
            raise HTTPException(
                status_code=404,
                detail=f"Variable with base name '{base_name}' not found in any year"
            )
        
        return VariableTemporalResponse(
            base_name=base_name,
            years=sorted(years_present),
            year_prefixes=year_prefixes,
            first_year=min(years_present),
            last_year=max(years_present),
            consistent_metadata=True,  # Could be enhanced to check actual consistency
            consistent_values=True  # Could be enhanced to check actual consistency
        )


@app.get("/waves", response_model=List[WaveInfo], tags=["General"])
async def get_waves():
    """Get information about all HRS waves (1-16)."""
    waves = []
    for year in sorted(HRS_YEARS):
        wave = get_wave_number(year)
        prefix = get_year_prefix(year)
        if wave:
            waves.append(WaveInfo(
                wave=wave,
                year=year,
                prefix=prefix or ""
            ))
    return waves


@app.get("/waves/{wave}", response_model=WaveInfo, tags=["General"])
async def get_wave_info(wave: int = PathParam(..., ge=1, le=16, description="Wave number (1-16)")):
    """Get information about a specific HRS wave."""
    year = get_year_from_wave(wave)
    if not year:
        raise HTTPException(status_code=404, detail=f"Wave {wave} not found")
    
    prefix = get_year_prefix(year)
    return WaveInfo(
        wave=wave,
        year=year,
        prefix=prefix or ""
    )


@app.get("/utils/extract-base-name", tags=["Utilities"])
async def extract_base_name_endpoint(
    variable_name: str = Query(..., description="Variable name with potential prefix")
):
    """Extract base variable name by removing year prefix."""
    base_name = extract_base_name(variable_name)
    return {
        "variable_name": variable_name,
        "base_name": base_name,
        "prefix": variable_name[:len(variable_name) - len(base_name)] if variable_name != base_name else ""
    }


@app.get("/utils/construct-variable-name", tags=["Utilities"])
async def construct_variable_name_endpoint(
    base_name: str = Query(..., description="Base variable name"),
    year: int = Query(..., description="Survey year (1992-2022)")
):
    """Construct variable name with year prefix."""
    if year not in HRS_YEARS:
        raise HTTPException(status_code=400, detail=f"Year {year} is not a valid HRS year")
    
    var_name = construct_variable_name(base_name, year)
    prefix = get_year_prefix(year)
    wave = get_wave_number(year)
    
    return {
        "base_name": base_name,
        "year": year,
        "wave": wave,
        "prefix": prefix or "",
        "variable_name": var_name
    }


@app.get("/utils/year-prefix", tags=["Utilities"])
async def get_year_prefix_endpoint(
    year: int = Query(..., description="Survey year (1992-2022)")
):
    """Get the variable name prefix for a given year."""
    if year not in HRS_YEARS:
        raise HTTPException(status_code=400, detail=f"Year {year} is not a valid HRS year")
    
    prefix = get_year_prefix(year)
    wave = get_wave_number(year)
    
    return {
        "year": year,
        "wave": wave,
        "prefix": prefix or "",
        "has_prefix": bool(prefix)
    }


@app.get("/utils/prefix-year", tags=["Utilities"])
async def get_prefix_year_endpoint(
    prefix: str = Query(..., description="Variable name prefix (e.g., 'R', 'Q', 'E')")
):
    """Get the year associated with a variable name prefix."""
    year = get_year_from_prefix(prefix)
    if not year:
        raise HTTPException(status_code=404, detail=f"Prefix '{prefix}' not found")
    
    wave = get_wave_number(year)
    return {
        "prefix": prefix,
        "year": year,
        "wave": wave
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
