"""Pydantic models for HRS Exit codebook data.

Exit codebooks (hrs_exit_codebook) cover exit questionnaire variables for years
1995–2022 (1995 AHEAD exit; 1996+ HRS exit). Variable naming uses the same
year-prefix convention as core (E=1996, F=1998, …).
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field


# Exit codebook years from config/sources.yaml (hrs_exit_codebook)
HRS_EXIT_YEARS: Set[int] = {
    1995, 1996, 1998, 2000, 2002, 2004, 2006, 2008,
    2010, 2012, 2014, 2016, 2018, 2020, 2022,
}


class ExitVariableLevel(str, Enum):
    """Level at which an exit variable is measured."""
    RESPONDENT = "Respondent"
    HOUSEHOLD = "Household"
    OTHER = "Other"


class ExitVariableType(str, Enum):
    """Data type of an exit variable."""
    CHARACTER = "Character"
    NUMERIC = "Numeric"


class ExitValueCode(BaseModel):
    """Single value code/label for an exit variable."""
    code: str = Field(..., description="Value code (e.g. '0', '1', 'Yes')")
    frequency: Optional[int] = Field(None, description="Frequency count")
    label: Optional[str] = Field(None, description="Human-readable label")
    is_missing: bool = Field(False, description="Whether this is a missing value")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "1",
                "frequency": 500,
                "label": "Yes",
                "is_missing": False,
            }
        }


class ExitVariable(BaseModel):
    """A variable from an HRS exit codebook."""
    name: str = Field(..., description="Variable name (e.g. EEXDATE, REXDATE)")
    year: int = Field(..., description="Survey year (1995–2022)")
    section: str = Field("", description="Section code or name")
    level: ExitVariableLevel = Field(
        ExitVariableLevel.RESPONDENT,
        description="Level at which variable is measured",
    )
    description: str = Field("", description="Variable description/label")
    type: ExitVariableType = Field(
        ExitVariableType.CHARACTER,
        description="Data type",
    )
    width: int = Field(0, description="Field width")
    decimals: int = Field(0, description="Decimal places")
    value_codes: List[ExitValueCode] = Field(
        default_factory=list,
        description="Value codes and labels",
    )
    has_value_codes: bool = Field(False, description="Whether variable has value codes")
    notes: Optional[str] = Field(None, description="Additional notes")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "REXDATE",
                "year": 2020,
                "section": "Exit",
                "level": "Respondent",
                "description": "Exit interview date",
                "type": "Character",
                "width": 8,
                "decimals": 0,
                "value_codes": [],
                "has_value_codes": False,
            }
        }


class ExitSection(BaseModel):
    """A section in an exit codebook."""
    code: str = Field(..., description="Section code or identifier")
    name: str = Field(..., description="Section name")
    level: ExitVariableLevel = Field(
        ExitVariableLevel.RESPONDENT,
        description="Level for this section",
    )
    year: int = Field(..., description="Survey year")
    variable_count: int = Field(0, description="Number of variables in section")
    variables: List[str] = Field(
        default_factory=list,
        description="Variable names in this section",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "code": "EX",
                "name": "Exit Interview",
                "level": "Respondent",
                "year": 2020,
                "variable_count": 50,
                "variables": ["REXDATE", "REXREAS"],
            }
        }


class ExitCodebook(BaseModel):
    """Parsed HRS exit codebook for one year."""
    source: str = Field(
        "hrs_exit_codebook",
        description="Source identifier from config",
    )
    year: int = Field(..., description="Survey year (1995–2022)")
    release_type: Optional[str] = Field(None, description="Release type if known")
    sections: List[ExitSection] = Field(
        default_factory=list,
        description="Sections in the codebook",
    )
    variables: List[ExitVariable] = Field(
        default_factory=list,
        description="All variables",
    )
    total_variables: int = Field(0, description="Total variable count")
    total_sections: int = Field(0, description="Total section count")
    levels: Set[ExitVariableLevel] = Field(
        default_factory=set,
        description="Levels present in this codebook",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Extra metadata (e.g. file path)",
    )
    parsed_at: datetime = Field(
        default_factory=datetime.now,
        description="When the codebook was parsed",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "source": "hrs_exit_codebook",
                "year": 2020,
                "total_variables": 200,
                "total_sections": 5,
                "levels": ["Respondent"],
            }
        }
