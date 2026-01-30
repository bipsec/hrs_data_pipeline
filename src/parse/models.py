"""Pydantic models for parsed HRS codebook entities.

This module defines a clean latent structure model for HRS (Health and Retirement Study) data,
capturing variables, value codes, sections, and their relationships across years.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Set, Any
from datetime import datetime
from enum import Enum


class VariableLevel(str, Enum):
    """Level at which a variable is measured."""
    HOUSEHOLD = "Household"
    RESPONDENT = "Respondent"
    JOBS = "Jobs"
    PENSION = "Pension"
    SIBLINGS = "Siblings"
    HH_MEMBER_CHILD = "HH Member Child"
    TO_CHILD = "To Child"
    FROM_CHILD = "From Child"
    HELPER = "Helper"


class VariableType(str, Enum):
    """Data type of a variable."""
    CHARACTER = "Character"
    NUMERIC = "Numeric"


class ValueCode(BaseModel):
    """Represents a single value code/label for a variable."""
    code: str = Field(..., description="The value code (e.g., '0', '1', 'Blank', '010003-959738')")
    frequency: Optional[int] = Field(None, description="Frequency count for this value")
    label: Optional[str] = Field(None, description="Human-readable label for this value")
    is_missing: bool = Field(False, description="Whether this represents a missing value (e.g., 'Blank')")
    is_range: bool = Field(False, description="Whether this code represents a range (e.g., '010003-959738')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "1",
                "frequency": 11485,
                "label": "Yes",
                "is_missing": False,
                "is_range": False
            }
        }


class VariableAssignment(BaseModel):
    """Represents an assignment or calculation for a variable."""
    expression: str = Field(..., description="The assignment expression or formula")
    reference_variables: List[str] = Field(default_factory=list, description="Variables referenced in the assignment")
    
    class Config:
        json_schema_extra = {
            "example": {
                "expression": "Init.A500_CurDate := SysDate",
                "reference_variables": []
            }
        }


class VariableReference(BaseModel):
    """Represents a reference to another variable or initialization."""
    reference: str = Field(..., description="The reference string (e.g., 'Init.A500_CurDate')")
    referenced_variable: Optional[str] = Field(None, description="The variable name being referenced, if extractable")
    
    class Config:
        json_schema_extra = {
            "example": {
                "reference": "Init.A500_CurDate",
                "referenced_variable": "A500"
            }
        }


class Variable(BaseModel):
    """Represents a variable from an HRS codebook with complete metadata."""
    # Core identification
    name: str = Field(..., description="Variable name (e.g., 'HHID', 'RSUBHH')")
    year: int = Field(..., description="Survey year")
    section: str = Field(..., description="Section code (e.g., 'PR', 'A', 'B')")
    level: VariableLevel = Field(..., description="Level at which variable is measured")
    
    # Metadata
    description: str = Field(..., description="Full variable description/label")
    type: VariableType = Field(..., description="Data type")
    width: int = Field(..., description="Field width")
    decimals: int = Field(0, description="Number of decimal places")
    
    # Value information
    value_codes: List[ValueCode] = Field(default_factory=list, description="List of value codes and labels")
    has_value_codes: bool = Field(False, description="Whether variable has discrete value codes")
    
    # Relationships and references
    assignments: List[VariableAssignment] = Field(default_factory=list, description="Assignments or calculations")
    references: List[VariableReference] = Field(default_factory=list, description="References to other variables")
    
    # Additional metadata
    is_derived: bool = Field(False, description="Whether variable is derived/calculated")
    is_identifier: bool = Field(False, description="Whether variable is an identifier (HHID, PN, etc.)")
    notes: Optional[str] = Field(None, description="Additional notes or special markers (e.g., '*')")
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "RSUBHH",
                "year": 2020,
                "section": "A",
                "level": "Respondent",
                "description": "2020 SUB HOUSEHOLD IDENTIFICATION NUMBER",
                "type": "Character",
                "width": 1,
                "decimals": 0,
                "value_codes": [
                    {"code": "0", "frequency": 13984, "label": "Original sample household...", "is_missing": False},
                    {"code": "1", "frequency": 907, "label": "Split household...", "is_missing": False}
                ],
                "has_value_codes": True,
                "is_identifier": True
            }
        }


class Section(BaseModel):
    """Represents a section of the codebook."""
    code: str = Field(..., description="Section code (e.g., 'PR', 'A', 'B')")
    name: str = Field(..., description="Section name (e.g., 'PRELOAD', 'COVERSCREEN')")
    level: VariableLevel = Field(..., description="Level for this section")
    year: int = Field(..., description="Survey year")
    variable_count: int = Field(0, description="Number of variables in this section")
    variables: List[str] = Field(default_factory=list, description="List of variable names in this section")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "A",
                "name": "COVERSCREEN",
                "level": "Respondent",
                "year": 2020,
                "variable_count": 45,
                "variables": ["HHID", "PN", "RSUBHH"]
            }
        }


class VariableTemporalMapping(BaseModel):
    """Maps a variable across years, tracking name changes and consistency."""
    base_name: str = Field(..., description="Base variable name without year prefix (e.g., 'SUBHH' from 'RSUBHH')")
    year_prefixes: Dict[int, str] = Field(default_factory=dict, description="Year to prefix mapping (e.g., {2020: 'R', 2018: 'Q'})")
    years: Set[int] = Field(default_factory=set, description="Years in which this variable appears")
    consistent_metadata: bool = Field(True, description="Whether metadata (type, width, etc.) is consistent across years")
    consistent_values: bool = Field(True, description="Whether value codes are consistent across years")
    
    class Config:
        json_schema_extra = {
            "example": {
                "base_name": "SUBHH",
                "year_prefixes": {2020: "R", 2018: "Q", 2016: "P"},
                "years": {2020, 2018, 2016},
                "consistent_metadata": True,
                "consistent_values": False
            }
        }


class Codebook(BaseModel):
    """Represents a complete parsed codebook for a survey year."""
    # Identification
    source: str = Field(..., description="Source identifier (e.g., 'hrs_core_codebook')")
    year: int = Field(..., description="Survey year")
    release_type: Optional[str] = Field(None, description="Release type (e.g., 'Final Release')")
    
    # Structure
    sections: List[Section] = Field(default_factory=list, description="Sections in the codebook")
    variables: List[Variable] = Field(default_factory=list, description="All variables in the codebook")
    
    # Statistics
    total_variables: int = Field(0, description="Total number of variables")
    total_sections: int = Field(0, description="Total number of sections")
    levels: Set[VariableLevel] = Field(default_factory=set, description="Levels present in this codebook")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    parsed_at: datetime = Field(default_factory=datetime.now, description="When the codebook was parsed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source": "hrs_core_codebook",
                "year": 2020,
                "release_type": "Final Release",
                "total_variables": 5000,
                "total_sections": 25,
                "levels": ["Household", "Respondent"]
            }
        }


class CrossYearVariableCatalog(BaseModel):
    """Catalog of variables across multiple years with temporal mappings."""
    base_variables: Dict[str, VariableTemporalMapping] = Field(
        default_factory=dict,
        description="Mapping from base variable name to temporal mapping"
    )
    year_codebooks: Dict[int, Codebook] = Field(
        default_factory=dict,
        description="Codebooks indexed by year"
    )
    years: Set[int] = Field(default_factory=set, description="All years in the catalog")
    
    def get_variable_across_years(self, base_name: str) -> List[Variable]:
        """Get all instances of a variable across years."""
        if base_name not in self.base_variables:
            return []
        
        mapping = self.base_variables[base_name]
        variables = []
        for year in mapping.years:
            codebook = self.year_codebooks.get(year)
            if codebook:
                # Find variable with year prefix
                prefix = mapping.year_prefixes.get(year, "")
                var_name = f"{prefix}{base_name}" if prefix else base_name
                var = next((v for v in codebook.variables if v.name == var_name), None)
                if var:
                    variables.append(var)
        return variables
    
    class Config:
        json_schema_extra = {
            "example": {
                "years": {2020, 2018, 2016},
                "base_variables": {
                    "SUBHH": {
                        "base_name": "SUBHH",
                        "year_prefixes": {2020: "R", 2018: "Q", 2016: "P"},
                        "years": {2020, 2018, 2016}
                    }
                }
            }
        }
