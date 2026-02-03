"""Pydantic models for parsed HRS codebook entities.

This module defines a clean latent structure model for HRS (Health and Retirement Study) data,
capturing variables, value codes, sections, and their relationships across all cycles (1992-2022).

Key Features:
- Comprehensive support for all HRS years (1992-2022, biennial waves 1-16)
- Year-to-prefix mapping for variable naming conventions (E=1996, F=1998, ..., R=2020, S=2022)
- Cross-year variable mapping with temporal tracking
- Support for all section codes (A-Z, PR, TN, LB, IO, COV, etc.)
- Support for all variable levels (Respondent, Household, Pension, Jobs, Siblings, etc.)
- Utility functions for extracting base names, constructing variable names, and wave calculations

Year Prefix Mapping:
- 1992-1994: No prefix (or different convention)
- 1996: E (Wave 3)
- 1998: F (Wave 4)
- 2000: G (Wave 5)
- 2002: H (Wave 6)
- 2004: I (Wave 7)
- 2006: J (Wave 8)
- 2008: K (Wave 9)
- 2010: L (Wave 10)
- 2012: M (Wave 11)
- 2014: N (Wave 12)
- 2016: P (Wave 13)
- 2018: Q (Wave 14)
- 2020: R (Wave 15)
- 2022: S (Wave 16)

Example Usage:
    >>> from src.models.cores import extract_base_name, construct_variable_name, get_wave_number
    >>> extract_base_name("RSUBHH")  # Returns "SUBHH"
    >>> construct_variable_name("SUBHH", 2020)  # Returns "RSUBHH"
    >>> get_wave_number(2020)  # Returns 15
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Set, Any, Tuple
from datetime import datetime
from enum import Enum

# Year-to-prefix mapping for HRS core data (1992-2022)
# This maps survey years to the letter prefix used in variable names
YEAR_PREFIX_MAP: Dict[int, str] = {
    1992: "",      # 1992 uses no prefix or different convention
    1993: "",      # AHEAD cohort
    1994: "",      # 1994 uses no prefix or different convention
    1995: "",      # AHEAD cohort
    1996: "E",     # Wave 3
    1998: "F",     # Wave 4
    2000: "G",     # Wave 5
    2002: "H",     # Wave 6
    2004: "I",     # Wave 7
    2006: "J",     # Wave 8
    2008: "K",     # Wave 9
    2010: "L",     # Wave 10
    2012: "M",     # Wave 11
    2014: "N",     # Wave 12
    2016: "P",     # Wave 13
    2018: "Q",     # Wave 14
    2020: "R",     # Wave 15
    2022: "S",     # Wave 16
}

# Reverse mapping: prefix to year
PREFIX_YEAR_MAP: Dict[str, int] = {v: k for k, v in YEAR_PREFIX_MAP.items() if v}

# All valid HRS years (1992-2022, biennial)
HRS_YEARS: Set[int] = {1992, 1994, 1996, 1998, 2000, 2002, 2004, 2006, 2008, 2010, 2012, 2014, 2016, 2018, 2020, 2022}

# AHEAD cohort years (merged with HRS)
AHEAD_YEARS: Set[int] = {1993, 1995}


def extract_base_name(var_name: str) -> str:
    """Extract base variable name by removing year prefixes (1992-2022).
    
    Examples:
        RSUBHH -> SUBHH (2020)
        QSUBHH -> SUBHH (2018)
        ESUBHH -> SUBHH (1996)
        HHID -> HHID (no prefix, appears in all years)
        PN -> PN (no prefix)
    
    Args:
        var_name: Variable name with potential year prefix
    
    Returns:
        Base variable name without prefix
    """
    # Check against known prefixes in reverse order (newest to oldest)
    for year in sorted(YEAR_PREFIX_MAP.keys(), reverse=True):
        prefix = YEAR_PREFIX_MAP[year]
        if prefix and var_name.startswith(prefix) and len(var_name) > len(prefix):
            rest = var_name[len(prefix):]
            # Validate that the rest looks like a variable name
            if rest and (rest[0].isupper() or rest[0].isdigit() or rest[0] == '_'):
                return rest
    
    # No prefix found, return as-is
    return var_name


def get_year_prefix(year: int) -> str:
    """Get the variable name prefix for a given year.
    
    Args:
        year: Survey year (1992-2022)
    
    Returns:
        Prefix string (e.g., 'R' for 2020, 'E' for 1996, '' for 1992-1994)
    """
    return YEAR_PREFIX_MAP.get(year, "")


def get_year_from_prefix(prefix: str) -> Optional[int]:
    """Get the year associated with a variable name prefix.
    
    Args:
        prefix: Variable name prefix (e.g., 'R', 'Q', 'E')
    
    Returns:
        Year if prefix is found, None otherwise
    """
    return PREFIX_YEAR_MAP.get(prefix)


def construct_variable_name(base_name: str, year: int) -> str:
    """Construct variable name with year prefix.
    
    Args:
        base_name: Base variable name (e.g., 'SUBHH')
        year: Survey year (1992-2022)
    
    Returns:
        Variable name with prefix (e.g., 'RSUBHH' for 2020, 'ESUBHH' for 1996)
    """
    prefix = get_year_prefix(year)
    if prefix:
        return f"{prefix}{base_name}"
    return base_name


def get_wave_number(year: int) -> Optional[int]:
    """Get HRS wave number for a given year.
    
    HRS waves are biennial starting from 1992:
    - Wave 1: 1992
    - Wave 2: 1994
    - Wave 3: 1996
    - ...
    - Wave 15: 2020
    - Wave 16: 2022
    
    Args:
        year: Survey year (1992-2022)
    
    Returns:
        Wave number (1-16) or None if year is not a valid HRS year
    """
    if year not in HRS_YEARS:
        return None
    # Wave 1 = 1992, Wave 2 = 1994, etc.
    # Formula: (year - 1992) / 2 + 1
    return ((year - 1992) // 2) + 1


def get_year_from_wave(wave: int) -> Optional[int]:
    """Get survey year from HRS wave number.
    
    Args:
        wave: Wave number (1-16)
    
    Returns:
        Survey year or None if wave is invalid
    """
    if wave < 1 or wave > 16:
        return None
    # Wave 1 = 1992, Wave 2 = 1994, etc.
    # Formula: 1992 + (wave - 1) * 2
    year = 1992 + (wave - 1) * 2
    return year if year in HRS_YEARS else None


class VariableLevel(str, Enum):
    """Level at which a variable is measured across all HRS cycles (1992-2022).
    
    Levels correspond to file suffixes in HRS data files:
    - _R: Respondent level
    - _H: Household level
    - _P: Pension level
    - _MC: Master Codes
    - _TC: To Child
    - _FC: From Child
    - _SB: Siblings
    - _JB: Jobs
    - _HP: Helper
    - _PR: Preload
    """
    HOUSEHOLD = "Household"           # _H suffix
    RESPONDENT = "Respondent"         # _R suffix
    JOBS = "Jobs"                     # _JB suffix
    PENSION = "Pension"               # _P suffix
    SIBLINGS = "Siblings"             # _SB suffix
    HH_MEMBER_CHILD = "HH Member Child"  # Child in household
    TO_CHILD = "To Child"             # _TC suffix
    FROM_CHILD = "From Child"         # _FC suffix
    HELPER = "Helper"                 # _HP suffix
    PRELOAD = "Preload"               # _PR suffix
    MASTER_CODES = "Master Codes"     # _MC suffix

# Section codes used across HRS cycles (1992-2022)
# These correspond to section letters in file names (e.g., H22A_R.txt = Section A, Respondent level)
HRS_SECTION_CODES: Set[str] = {
    "PR",  # Preload
    "A",   # Coverscreen/Demographics
    "B",   # Demographics/Background
    "C",   # Cognition
    "D",   # Health
    "E",   # Family/Children
    "F",   # Work/Employment
    "G",   # Income/Assets
    "H",   # Housing
    "I",   # Insurance
    "J",   # Pensions
    "K",   # Expectations
    "L",   # Psychosocial
    "M",   # Medications
    "N",   # Health Conditions
    "P",   # Physical Measures
    "Q",   # Quality of Life
    "R",   # Retirement
    "S",   # Social Security
    "T",   # Transfers
    "U",   # Internet Use
    "V",   # Volunteering
    "W",   # Work History
    "Y",   # Year-specific modules
    "TN",  # Telephone Number
    "LB",  # Leave Behind
    "IO",  # Industry/Occupation
    "COV", # Coversheet
}


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
    """Represents a section of the codebook across all HRS cycles (1992-2022)."""
    code: str = Field(..., description="Section code (e.g., 'PR', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'Y', 'TN', 'LB', 'IO', 'COV')")
    name: str = Field(..., description="Section name (e.g., 'PRELOAD', 'COVERSCREEN', 'DEMOGRAPHICS', 'COGNITION', 'HEALTH')")
    level: VariableLevel = Field(..., description="Level for this section (Respondent, Household, Pension, etc.)")
    year: int = Field(..., description="Survey year (1992-2022)")
    variable_count: int = Field(0, description="Number of variables in this section")
    variables: List[str] = Field(default_factory=list, description="List of variable names in this section")
    file_suffix: Optional[str] = Field(None, description="File suffix for this section (e.g., '_R', '_H', '_P')")
    
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
    """Maps a variable across years (1992-2022), tracking name changes and consistency."""
    base_name: str = Field(..., description="Base variable name without year prefix (e.g., 'SUBHH' from 'RSUBHH', 'ESUBHH')")
    year_prefixes: Dict[int, str] = Field(default_factory=dict, description="Year to prefix mapping (e.g., {2020: 'R', 2018: 'Q', 1996: 'E'})")
    years: Set[int] = Field(default_factory=set, description="Years in which this variable appears (1992-2022)")
    consistent_metadata: bool = Field(True, description="Whether metadata (type, width, etc.) is consistent across years")
    consistent_values: bool = Field(True, description="Whether value codes are consistent across years")
    first_year: Optional[int] = Field(None, description="First year this variable appeared")
    last_year: Optional[int] = Field(None, description="Last year this variable appeared")
    year_gaps: List[Tuple[int, int]] = Field(default_factory=list, description="Gaps in years where variable is missing (start_year, end_year)")
    
    def get_variable_name_for_year(self, year: int) -> Optional[str]:
        """Get the variable name for a specific year."""
        prefix = self.year_prefixes.get(year, "")
        if prefix:
            return f"{prefix}{self.base_name}"
        return self.base_name if year in self.years else None
    
    class Config:
        json_schema_extra = {
            "example": {
                "base_name": "SUBHH",
                "year_prefixes": {2020: "R", 2018: "Q", 2016: "P", 1996: "E"},
                "years": {2020, 2018, 2016, 1996},
                "consistent_metadata": True,
                "consistent_values": False,
                "first_year": 1996,
                "last_year": 2020
            }
        }


class Codebook(BaseModel):
    """Represents a complete parsed codebook for a survey year (1992-2022)."""
    # Identification
    source: str = Field(..., description="Source identifier (e.g., 'hrs_core_codebook')")
    year: int = Field(..., description="Survey year (1992-2022)")
    release_type: Optional[str] = Field(None, description="Release type (e.g., 'Final Release', 'Version 3')")
    wave: Optional[int] = Field(None, description="HRS wave number (e.g., 3 for 1996, 15 for 2020)")
    
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
    """Catalog of variables across all HRS years (1992-2022) with temporal mappings."""
    base_variables: Dict[str, VariableTemporalMapping] = Field(
        default_factory=dict,
        description="Mapping from base variable name to temporal mapping"
    )
    year_codebooks: Dict[int, Codebook] = Field(
        default_factory=dict,
        description="Codebooks indexed by year (1992-2022)"
    )
    years: Set[int] = Field(default_factory=set, description="All years in the catalog (subset of 1992-2022)")
    
    def get_variable_across_years(self, base_name: str, years: Optional[List[int]] = None) -> List[Variable]:
        """Get all instances of a variable across specified years (or all years if not specified).
        
        Args:
            base_name: Base variable name (e.g., 'SUBHH')
            years: Optional list of years to retrieve. If None, returns all years.
        
        Returns:
            List of Variable objects across the specified years
        """
        if base_name not in self.base_variables:
            return []
        
        mapping = self.base_variables[base_name]
        target_years = years if years is not None else sorted(mapping.years)
        variables = []
        
        for year in target_years:
            if year not in mapping.years:
                continue
                
            codebook = self.year_codebooks.get(year)
            if codebook:
                # Find variable with year prefix
                var_name = mapping.get_variable_name_for_year(year)
                if var_name:
                    var = next((v for v in codebook.variables if v.name == var_name), None)
                    if var:
                        variables.append(var)
        
        return variables
    
    def get_variable_for_year(self, base_name: str, year: int) -> Optional[Variable]:
        """Get a variable instance for a specific year.
        
        Args:
            base_name: Base variable name (e.g., 'SUBHH')
            year: Survey year (1992-2022)
        
        Returns:
            Variable object for the specified year, or None if not found
        """
        variables = self.get_variable_across_years(base_name, years=[year])
        return variables[0] if variables else None
    
    def get_years_for_variable(self, base_name: str) -> List[int]:
        """Get all years in which a variable appears.
        
        Args:
            base_name: Base variable name
        
        Returns:
            Sorted list of years
        """
        if base_name not in self.base_variables:
            return []
        return sorted(self.base_variables[base_name].years)
    
    def get_continuous_years(self, base_name: str) -> List[Tuple[int, int]]:
        """Get continuous year ranges for a variable.
        
        Args:
            base_name: Base variable name
        
        Returns:
            List of (start_year, end_year) tuples for continuous ranges
        """
        if base_name not in self.base_variables:
            return []
        
        years = sorted(self.base_variables[base_name].years)
        if not years:
            return []
        
        ranges = []
        start = years[0]
        end = years[0]
        
        for i in range(1, len(years)):
            if years[i] == end + 2:  # HRS is biennial (every 2 years)
                end = years[i]
            else:
                ranges.append((start, end))
                start = years[i]
                end = years[i]
        
        ranges.append((start, end))
        return ranges
    
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
