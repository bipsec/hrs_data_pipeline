"""Categorization endpoints: variable categorization by section, level, type, etc."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from ...dependencies import get_mongodb_client
from ...models import (
    CategorizationResponse,
    VariableCategoryResponse,
    SpecialCategoriesResponse,
    BySectionResponse,
    ByLevelResponse,
    ByTypeResponse,
    ByBaseNameResponse,
)
from ....discovery.discover_codebooks import (
    VariableCategory,
    VariableCategorization,
    build_categorization_from_codebooks,
)
from ....models.cores import HRS_LEGACY_YEARS, HRS_MODERN_YEARS

router = APIRouter(tags=["Categorization"], prefix="/categorization")


def _category_to_response(cat: VariableCategory) -> VariableCategoryResponse:
    """Convert discovery VariableCategory (with sets) to API VariableCategoryResponse (lists)."""
    return VariableCategoryResponse(
        name=cat.name,
        description=cat.description,
        variable_names=list(cat.variable_names),
        count=cat.count,
        years=sorted(cat.years) if cat.years else [],
        sections=sorted(cat.sections) if cat.sections else [],
        levels=sorted(cat.levels) if cat.levels else [],
    )


def _dict_categories(
    d: Dict[str, VariableCategory],
) -> Dict[str, VariableCategoryResponse]:
    return {k: _category_to_response(v) for k, v in d.items()}


def _categorization_to_response(c: VariableCategorization) -> CategorizationResponse:
    """Convert discovery VariableCategorization to API CategorizationResponse."""
    special = SpecialCategoriesResponse(
        identifiers=_category_to_response(c.identifiers),
        derived=_category_to_response(c.derived),
        with_value_codes=_category_to_response(c.with_value_codes),
        without_value_codes=_category_to_response(c.without_value_codes),
        year_prefixed=_category_to_response(c.year_prefixed),
        no_prefix=_category_to_response(c.no_prefix),
    )
    return CategorizationResponse(
        by_section=_dict_categories(c.by_section),
        by_level=_dict_categories(c.by_level),
        by_type=_dict_categories(c.by_type),
        by_base_name=_dict_categories(c.by_base_name),
        special_categories=special,
        total_variables=c.total_variables,
        total_years=c.total_years,
        years_covered=sorted(c.years_covered) if c.years_covered else [],
    )


async def _fetch_categorization(
    year: Optional[int] = None,
    source: Optional[str] = None,
    core_period: Optional[str] = None,
) -> VariableCategorization:
    """Fetch codebooks from MongoDB and build categorization. Raises 404 if no codebooks."""
    client = get_mongodb_client()
    collection = client.get_collection("codebooks")
    query: Dict[str, Any] = {}
    if year is not None:
        query["year"] = year
    elif core_period:
        cp = core_period.lower()
        if cp == "legacy":
            query["year"] = {"$in": sorted(HRS_LEGACY_YEARS)}
        elif cp == "modern":
            query["year"] = {"$in": sorted(HRS_MODERN_YEARS)}
    if source:
        query["source"] = source
    codebooks = list(collection.find(query, {"year": 1, "source": 1, "variables": 1}))
    if not codebooks:
        raise HTTPException(status_code=404, detail="No codebooks found for the given filters")
    return build_categorization_from_codebooks(codebooks)


@router.get("", response_model=CategorizationResponse)
async def get_categorization(
    year: Optional[int] = Query(None, description="Filter by year"),
    source: Optional[str] = Query(None, description="Filter by source (e.g., hrs_core_codebook)"),
    core_period: Optional[str] = Query(
        None,
        description="Filter by core period: 'legacy' (1992-2004) or 'modern' (2008-2022)",
    ),
):
    """Get full variable categorization (by section, level, type, base name, and special categories)."""
    c = await _fetch_categorization(year=year, source=source, core_period=core_period)
    return _categorization_to_response(c)


@router.get("/sections", response_model=BySectionResponse)
async def get_categorization_by_section(
    year: Optional[int] = Query(None, description="Filter by year"),
    source: Optional[str] = Query(None, description="Filter by source"),
    core_period: Optional[str] = Query(None, description="'legacy' or 'modern'"),
):
    """Get variable categorization by section only."""
    c = await _fetch_categorization(year=year, source=source, core_period=core_period)
    return BySectionResponse(sections=_dict_categories(c.by_section))


@router.get("/levels", response_model=ByLevelResponse)
async def get_categorization_by_level(
    year: Optional[int] = Query(None, description="Filter by year"),
    source: Optional[str] = Query(None, description="Filter by source"),
    core_period: Optional[str] = Query(None, description="'legacy' or 'modern'"),
):
    """Get variable categorization by level only."""
    c = await _fetch_categorization(year=year, source=source, core_period=core_period)
    return ByLevelResponse(levels=_dict_categories(c.by_level))


@router.get("/types", response_model=ByTypeResponse)
async def get_categorization_by_type(
    year: Optional[int] = Query(None, description="Filter by year"),
    source: Optional[str] = Query(None, description="Filter by source"),
    core_period: Optional[str] = Query(None, description="'legacy' or 'modern'"),
):
    """Get variable categorization by variable type only."""
    c = await _fetch_categorization(year=year, source=source, core_period=core_period)
    return ByTypeResponse(types=_dict_categories(c.by_type))


@router.get("/base-names", response_model=ByBaseNameResponse)
async def get_categorization_by_base_name(
    year: Optional[int] = Query(None, description="Filter by year"),
    source: Optional[str] = Query(None, description="Filter by source"),
    core_period: Optional[str] = Query(None, description="'legacy' or 'modern'"),
):
    """Get variable categorization by base variable name only."""
    c = await _fetch_categorization(year=year, source=source, core_period=core_period)
    return ByBaseNameResponse(base_names=_dict_categories(c.by_base_name))


@router.get("/special", response_model=SpecialCategoriesResponse)
async def get_categorization_special(
    year: Optional[int] = Query(None, description="Filter by year"),
    source: Optional[str] = Query(None, description="Filter by source"),
    core_period: Optional[str] = Query(None, description="'legacy' or 'modern'"),
):
    """Get special categories only (identifiers, derived, value-codes, prefix-based)."""
    c = await _fetch_categorization(year=year, source=source, core_period=core_period)
    return SpecialCategoriesResponse(
        identifiers=_category_to_response(c.identifiers),
        derived=_category_to_response(c.derived),
        with_value_codes=_category_to_response(c.with_value_codes),
        without_value_codes=_category_to_response(c.without_value_codes),
        year_prefixed=_category_to_response(c.year_prefixed),
        no_prefix=_category_to_response(c.no_prefix),
    )
