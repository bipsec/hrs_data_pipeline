"""FastAPI application for HRS data pipeline API."""

from fastapi import FastAPI, HTTPException, Query, Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from pathlib import Path

from ..database.mongodb_client import MongoDBClient
from ..parse.models import Variable, ValueCode, Section, Codebook, VariableLevel, VariableType

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
        
        return YearsResponse(years=years, sources=sources)


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
            "sources": sorted(codebooks_collection.distinct("source"))
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
