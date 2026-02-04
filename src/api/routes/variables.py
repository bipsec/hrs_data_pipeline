"""Variable endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path as PathParam

from ..dependencies import get_mongodb_client
from ..models import VariableSummary, VariableDetail, VariableTemporalResponse
from ...models.cores import get_year_prefix, construct_variable_name

router = APIRouter(tags=["Variables"])


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
    source: str = Query("hrs_core_codebook", description="Source name"),
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
    source: str = Query("hrs_core_codebook", description="Source name"),
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
    source: str = Query("hrs_core_codebook", description="Source name"),
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
