"""API response/summary models for HRS pipeline."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from ...models.cores import (
    Variable,
    HRS_YEARS,
    HRS_LEGACY_YEARS,
    HRS_MODERN_YEARS,
    YEAR_PREFIX_MAP,
)


class VariableSummary(BaseModel):
    """Summary of a variable for search/list results."""
    name: str
    year: int
    section: str
    level: str
    description: str
    type: str


class VariableDetail(Variable):
    """Full variable details (extends core Variable)."""
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
    core_period: Optional[str] = None
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
    hrs_legacy_years: List[int] = Field(default_factory=lambda: sorted(list(HRS_LEGACY_YEARS)))
    hrs_modern_years: List[int] = Field(default_factory=lambda: sorted(list(HRS_MODERN_YEARS)))
    year_prefix_map: Dict[int, str] = Field(default_factory=lambda: dict(YEAR_PREFIX_MAP))


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


# --- Categorizer API response models ---


class VariableCategoryResponse(BaseModel):
    """API representation of a single variable category (section, level, type, or special)."""
    name: str
    description: str
    variable_names: List[str] = Field(default_factory=list)
    count: int = 0
    years: List[int] = Field(default_factory=list)
    sections: List[str] = Field(default_factory=list)
    levels: List[str] = Field(default_factory=list)


class SpecialCategoriesResponse(BaseModel):
    """Modular group: identifier, derived, value-codes, and prefix-based categories."""
    identifiers: VariableCategoryResponse
    derived: VariableCategoryResponse
    with_value_codes: VariableCategoryResponse
    without_value_codes: VariableCategoryResponse
    year_prefixed: VariableCategoryResponse
    no_prefix: VariableCategoryResponse


class BySectionResponse(BaseModel):
    """Categorization by section only."""
    sections: Dict[str, VariableCategoryResponse] = Field(default_factory=dict)


class ByLevelResponse(BaseModel):
    """Categorization by level only."""
    levels: Dict[str, VariableCategoryResponse] = Field(default_factory=dict)


class ByTypeResponse(BaseModel):
    """Categorization by variable type only."""
    types: Dict[str, VariableCategoryResponse] = Field(default_factory=dict)


class ByBaseNameResponse(BaseModel):
    """Categorization by base variable name only."""
    base_names: Dict[str, VariableCategoryResponse] = Field(default_factory=dict)


class CategorizationResponse(BaseModel):
    """Full variable categorization: by dimension (section/level/type/base_name) and special categories."""
    by_section: Dict[str, VariableCategoryResponse] = Field(default_factory=dict)
    by_level: Dict[str, VariableCategoryResponse] = Field(default_factory=dict)
    by_type: Dict[str, VariableCategoryResponse] = Field(default_factory=dict)
    by_base_name: Dict[str, VariableCategoryResponse] = Field(default_factory=dict)
    special_categories: SpecialCategoriesResponse
    total_variables: int = 0
    total_years: int = 0
    years_covered: List[int] = Field(default_factory=list)


# --- Exit codebook API response models ---

EXIT_SOURCE = "hrs_exit_codebook"


class ExitValueCodeResponse(BaseModel):
    """Value code for an exit variable."""
    code: str
    frequency: Optional[int] = None
    label: Optional[str] = None
    is_missing: bool = False


class ExitVariableSummary(BaseModel):
    """Summary of an exit variable for list/search results."""
    name: str
    year: int
    section: str
    level: str
    description: str
    type: str


class ExitVariableDetail(BaseModel):
    """Full exit variable details."""
    name: str
    year: int
    section: str
    level: str
    description: str
    type: str
    width: int = 0
    decimals: int = 0
    value_codes: List[ExitValueCodeResponse] = Field(default_factory=list)
    has_value_codes: bool = False
    notes: Optional[str] = None


class ExitSectionResponse(BaseModel):
    """Exit section response."""
    code: str
    name: str
    level: str
    year: int
    variable_count: int
    variables: List[str]


class ExitCodebookSummary(BaseModel):
    """Exit codebook summary response."""
    source: str = EXIT_SOURCE
    year: int
    release_type: Optional[str] = None
    total_variables: int
    total_sections: int
    levels: List[str]


class ExitSearchResponse(BaseModel):
    """Exit variable search response."""
    query: str
    total: int
    results: List[ExitVariableSummary]
    limit: int
