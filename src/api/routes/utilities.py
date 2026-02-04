"""Utility endpoints (extract base name, construct variable name, year/prefix)."""

from fastapi import APIRouter, HTTPException, Query

from ...models.cores import (
    HRS_YEARS,
    extract_base_name,
    construct_variable_name,
    get_year_prefix,
    get_year_from_prefix,
    get_wave_number,
)

router = APIRouter(tags=["Utilities"])


@router.get("/utils/extract-base-name")
async def extract_base_name_endpoint(
    variable_name: str = Query(..., description="Variable name with potential prefix"),
):
    """Extract base variable name by removing year prefix."""
    base_name = extract_base_name(variable_name)
    return {
        "variable_name": variable_name,
        "base_name": base_name,
        "prefix": variable_name[: len(variable_name) - len(base_name)] if variable_name != base_name else "",
    }


@router.get("/utils/construct-variable-name")
async def construct_variable_name_endpoint(
    base_name: str = Query(..., description="Base variable name"),
    year: int = Query(..., description="Survey year (1992-2022)"),
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
        "variable_name": var_name,
    }


@router.get("/utils/year-prefix")
async def get_year_prefix_endpoint(
    year: int = Query(..., description="Survey year (1992-2022)"),
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
        "has_prefix": bool(prefix),
    }


@router.get("/utils/prefix-year")
async def get_prefix_year_endpoint(
    prefix: str = Query(..., description="Variable name prefix (e.g., 'R', 'Q', 'E')"),
):
    """Get the year associated with a variable name prefix."""
    year = get_year_from_prefix(prefix)
    if not year:
        raise HTTPException(status_code=404, detail=f"Prefix '{prefix}' not found")
    wave = get_wave_number(year)
    return {"prefix": prefix, "year": year, "wave": wave}
