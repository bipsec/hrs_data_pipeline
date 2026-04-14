from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Set, Any, Tuple
from datetime import datetime

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
    HOUSEHOLD = "Household"           
    RESPONDENT = "Respondent"    
    OTHER_PERSON = "Other Person"     
    JOBS = "Jobs"                     
    PENSION = "Pension"               
    SIBLINGS = "Siblings"             
    HH_MEMBER_CHILD = "HH Member Child"
    TO_CHILD = "To Child"             
    FROM_CHILD = "From Child"         
    HELPER = "Helper"                 
    PRELOAD = "Preload"               
    MASTER_CODES = "Master Codes"
    REMOVED = "Removed"                 # For variables that were removed in certain years     

class Ahead1993ValueCode(BaseModel):
    """Represents a single value code/label for a variable."""
    code: str = Field(..., description="The value code (e.g., '0', '1', 'Blank', '010003-959738')")
    frequency: Optional[Dict[str, Any]] = Field(None, description="Frequency count for this value " \
    "code can have multiple frequencies for different levels (e.g., {'Respondent': 5000, 'Household': 3000})")
    label: Optional[str] = Field(None, description="Human-readable label for this value")
    is_missing: bool = Field(False, description="Whether this represents a missing value (e.g., 'Blank')")
    is_range: bool = Field(False, description="Whether this code represents a range (e.g., '010003-959738')")
    
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "1",
                "frequency": {"Respondent": 11485},
                "label": "Yes",
                "is_missing": False,
                "is_range": False
            }
        }


class Ahead1993Variable(BaseModel):
    """Represents a variable from an HRS codebook with complete metadata."""
    # Core identification
    name: str = Field(..., description="Variable name (e.g., 'HHID', 'RSUBHH')")
    year: int = Field(..., description="Survey year")
    section: str = Field(..., description="Section code (e.g., 'PR', 'A', 'B')")
    levels: List[VariableLevel] = Field(..., description="Level at which variable is measured")
    is_skipped: bool = Field(False, description="Whether the value codes were skipped for this variable "
    "(1993 has inconsistant format and would be difficult to parse completely)")
    
    # Metadata
    description: str = Field(..., description="Full variable description/label")
    
    # Value information
    value_codes: List[Ahead1993ValueCode] = Field(default_factory=list, description="List of value codes and labels")
    has_value_codes: bool = Field(False, description="Whether variable has discrete value codes")
    
   
    class Config:
        json_schema_extra = {
            "example": {
                "name": "V100",
                "year": 1993,
                "section": "A",
                "levels": ["Respondent"],
                "description": "EXAMPLE DESCRIPTION",
                "value_codes": [
                    {"code": "0", "frequency": {"Respondent": 13984}, "label": "Original sample household...", "is_missing": False},
                    {"code": "1", "frequency": {"Respondent": 907}, "label": "Split household...", "is_missing": False}
                ],
                "has_value_codes": True,
                "is_skiped": False
            }
        }

class Ahead1993Section(BaseModel):
    """Represents a section of the codebook across all HRS cycles (1992-2022)."""
    code: str = Field(..., description="Section code (e.g., 'PR', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'Y', 'TN', 'LB', 'IO', 'COV')")
    name: str = Field(..., description="Section name (e.g., 'PRELOAD', 'COVERSCREEN', 'DEMOGRAPHICS', 'COGNITION', 'HEALTH')")
    levels: set[VariableLevel] = Field(..., description="Levels for this section (Respondent, Household, Pension, etc.)")
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

class Ahead1993Codebook(BaseModel):
    """Represents a complete parsed codebook for a survey year (1992-2022).
    
    Use CodebookLegacy for 1992-2004 (different conventions) and CodebookModern for 2008-2022.
    """
    # Identification
    source: str = Field(..., description="Source identifier (e.g., 'hrs_core_codebook')")
    year: int = Field(..., description="Survey year (1992-2022)")
    release_type: Optional[str] = Field(None, description="Release type (e.g., 'Final Release', 'Version 3')")
    wave: Optional[int] = Field(None, description="HRS wave number (e.g., 3 for 1996, 15 for 2020)")
    
    
    # Structure
    sections: List[Ahead1993Section] = Field(default_factory=list, description="Sections in the codebook")
    variables: List[Ahead1993Variable] = Field(default_factory=list, description="All variables in the codebook")
    
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