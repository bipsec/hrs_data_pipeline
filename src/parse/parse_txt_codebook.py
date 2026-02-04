"""Parse text codebook files to extract variable information according to the model structure."""

import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from datetime import datetime

from src.models.cores import (
    Codebook,
    CodebookLegacy,
    CodebookModern,
    Variable,
    ValueCode,
    Section,
    VariableLevel,
    VariableType,
    VariableAssignment,
    VariableReference,
    CoreDataPeriod,
    get_core_period,
    get_wave_number,
)


def parse_txt_codebook(
    txt_path: Path,
    source: str = "hrs_core_codebook",
    year: Optional[int] = None,
) -> Codebook:
    """Parse a text codebook file and extract variables according to the model.
    
    Returns CodebookLegacy for years 1992-2004 and CodebookModern for 2006-2022.
    
    Args:
        txt_path: Path to the text codebook file
        source: Source identifier (e.g., 'hrs_core_codebook')
        year: Survey year (extracted from filename if not provided)
    
    Returns:
        Parsed Codebook (CodebookLegacy or CodebookModern) by core period
    """
    if not txt_path.exists():
        raise FileNotFoundError(f"Codebook file not found: {txt_path}")
    
    # Extract year from filename if not provided
    if year is None:
        year = _extract_year_from_filename(txt_path)
    
    content = txt_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()
    
    # Parse header/metadata
    release_type = _extract_release_type(content)
    
    # Parse sections and variables
    sections: Dict[str, Section] = {}
    variables: List[Variable] = []
    current_section: Optional[str] = None
    current_section_name: Optional[str] = None
    current_level: Optional[VariableLevel] = None
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check for section header
        # 2002/2004: "SECTION PR: Preload (Household)"; modern: "Section A: Name (Level)"
        section_match = re.match(
            r"(?i)^section\s+([A-Z]+):\s+(.+?)(?:\s+\((.+?)\))?\s*$", line
        )
        if section_match:
            current_section = section_match.group(1)
            current_section_name = section_match.group(2).strip()
            level_str = section_match.group(3).strip() if section_match.group(3) else "Respondent"
            current_level = _parse_level(level_str)
            
            # Create or update section
            if current_section not in sections:
                sections[current_section] = Section(
                    code=current_section,
                    name=current_section_name,
                    level=current_level,
                    year=year,
                )
            i += 1
            continue
        
        # Check for variable definition
        # Modern: VARNAME                         DESCRIPTION (name and description on same line)
        # Legacy: VARNAME alone, then metadata line with Type/Width; or VARNAME, description line, then metadata
        var_match = re.match(r"^([A-Z0-9_]+)\s{2,}(.+)$", line)
        var_name_only = re.match(r"^([A-Z0-9_]+)\s*$", line) and current_section and line.strip()
        if (var_match or var_name_only) and current_section:
            if var_match:
                var_name = var_match.group(1).strip()
                var_description = var_match.group(2).strip()
                metadata_line_idx = i + 1
            else:
                var_name = line.strip()
                var_description = var_name
                metadata_line_idx = i + 1
                if i + 2 < len(lines):
                    next_ln = lines[i + 1].strip()
                    next_next = lines[i + 2].strip()
                    if _parse_variable_metadata(next_next, var_name, next_ln or var_description,
                                                current_section, current_level, year) and not _parse_variable_metadata(
                        next_ln, var_name, var_description, current_section, current_level, year
                    ):
                        var_description = next_ln or var_description
                        metadata_line_idx = i + 2
            # 2002/2004: metadata can follow after 0 or 1 blank lines; scan forward
            var_data = None
            if metadata_line_idx < len(lines):
                for offset in range(0, min(4, len(lines) - metadata_line_idx)):
                    candidate_idx = metadata_line_idx + offset
                    metadata_line = lines[candidate_idx].strip()
                    if not metadata_line:
                        continue
                    var_data = _parse_variable_metadata(metadata_line, var_name, var_description,
                                                       current_section, current_level, year)
                    if var_data:
                        metadata_line_idx = candidate_idx
                        break
                else:
                    var_data = None
            if var_data:
                # Skip variable name line and any description line, then metadata line
                lines_to_skip = (metadata_line_idx - i) + 1
                i += lines_to_skip
                # Parse value codes and assignments
                value_codes, assignments, references, notes = _parse_variable_content(
                    lines, i, var_data
                )
                var_data["value_codes"] = value_codes
                var_data["assignments"] = assignments
                var_data["references"] = references
                var_data["notes"] = notes
                var_data["has_value_codes"] = len(value_codes) > 0
                var_data["is_identifier"] = _is_identifier(var_name, var_description)
                variable = Variable(**var_data)
                variables.append(variable)
                sections[current_section].variables.append(var_name)
                sections[current_section].variable_count += 1
                while i < len(lines) and not _is_separator(lines[i]) and not _is_variable_start(lines[i]):
                    i += 1
                continue
        
        i += 1
    
    # Update section statistics
    for section in sections.values():
        section.variable_count = len(section.variables)
    
    # Collect all levels
    levels = set()
    for var in variables:
        levels.add(var.level)
    
    # Build codebook payload and use period-specific model (Legacy 1992-2004 vs Modern 2008-2022)
    period = get_core_period(year)
    wave = get_wave_number(year)
    payload = {
        "source": source,
        "year": year,
        "release_type": release_type,
        "wave": wave,
        "core_period": period,
        "sections": list(sections.values()),
        "variables": variables,
        "total_variables": len(variables),
        "total_sections": len(sections),
        "levels": levels,
        "metadata": {
            "file_path": str(txt_path),
            "file_name": txt_path.name,
        },
        "parsed_at": datetime.now(),
    }
    if period == CoreDataPeriod.LEGACY:
        return CodebookLegacy(**payload)
    return CodebookModern(**payload)


def _extract_year_from_filename(path: Path) -> int:
    """Extract year from filename (e.g., h2020cb.txt -> 2020)."""
    name = path.stem
    year_match = re.search(r"(\d{4})", name)
    if year_match:
        return int(year_match.group(1))
    # Try parent directory
    parent = path.parent.name
    year_match = re.search(r"(\d{4})", parent)
    if year_match:
        return int(year_match.group(1))
    raise ValueError(f"Could not extract year from path: {path}")


def _extract_release_type(content: str) -> Optional[str]:
    """Extract release type from header (e.g., 'Final Release')."""
    match = re.search(r"HRS\s+\d{4}\s+(.+?)\s*$", content[:500], re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def _parse_level(level_str: str) -> VariableLevel:
    """Parse level string to VariableLevel enum."""
    level_map = {
        "Household": VariableLevel.HOUSEHOLD,
        "Respondent": VariableLevel.RESPONDENT,
        "Jobs": VariableLevel.JOBS,
        "Pension": VariableLevel.PENSION,
        "Siblings": VariableLevel.SIBLINGS,
        "HH Member Child": VariableLevel.HH_MEMBER_CHILD,
        "To Child": VariableLevel.TO_CHILD,
        "From Child": VariableLevel.FROM_CHILD,
        "Helper": VariableLevel.HELPER,
    }
    return level_map.get(level_str, VariableLevel.RESPONDENT)


def _parse_variable_metadata(
    metadata_line: str,
    var_name: str,
    var_description: str,
    section: str,
    level: VariableLevel,
    year: int,
) -> Optional[Dict]:
    """Parse variable metadata line.
    
    Modern: Section: PR    Level: Household       Type: Character  Width: 6   Decimals: 0
    Legacy (1992-2004): may have Type/Width without Section: prefix; use current section/level.
    """
    # Extract section from line if present (modern format)
    section_match = re.search(r"[Ss]ection:\s*([A-Z]+)", metadata_line)
    use_section = section_match.group(1) if section_match else section
    
    # Legacy: require at least Type: or Width: to consider this a metadata line
    type_match = re.search(r"Type:\s*(\w+)", metadata_line)
    width_match = re.search(r"Width:\s*(\d+)", metadata_line)
    if not type_match and not width_match:
        return None
    
    # Extract level
    level_match = re.search(r"Level:\s*([^T]+?)(?:\s+Type:|$)", metadata_line)
    level_str = level_match.group(1).strip() if level_match else str(level.value)
    parsed_level = _parse_level(level_str)
    
    var_type = VariableType.CHARACTER
    if type_match:
        type_str = type_match.group(1).strip()
        var_type = VariableType.CHARACTER if "Character" in type_str else VariableType.NUMERIC
    
    width = int(width_match.group(1)) if width_match else 0
    
    decimals_match = re.search(r"Decimals:\s*(\d+)", metadata_line)
    decimals = int(decimals_match.group(1)) if decimals_match else 0
    
    return {
        "name": var_name,
        "year": year,
        "section": use_section,
        "level": parsed_level,
        "description": var_description,
        "type": var_type,
        "width": width,
        "decimals": decimals,
    }


def _parse_variable_content(
    lines: List[str],
    start_idx: int,
    var_data: Dict,
) -> Tuple[List[ValueCode], List[VariableAssignment], List[VariableReference], Optional[str]]:
    """Parse value codes, assignments, and references for a variable."""
    value_codes: List[ValueCode] = []
    assignments: List[VariableAssignment] = []
    references: List[VariableReference] = []
    notes: Optional[str] = None
    
    i = start_idx
    in_value_section = False
    current_label_lines: List[str] = []
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Stop at separator
        if _is_separator(line):
            break
        
        # Check for assignment (ASSIGN: ...)
        assign_match = re.match(r"ASSIGN:\s*(.+)", line, re.IGNORECASE)
        if assign_match:
            expr = assign_match.group(1).strip()
            # Extract referenced variables
            ref_vars = re.findall(r"([A-Z]\d+[A-Z0-9_]*)", expr)
            assignments.append(VariableAssignment(
                expression=expr,
                reference_variables=ref_vars,
            ))
            i += 1
            continue
        
        # Check for reference (Ref: ...)
        ref_match = re.match(r"Ref:\s*(.+)", line, re.IGNORECASE)
        if ref_match:
            ref_str = ref_match.group(1).strip()
            # Try to extract variable name
            ref_var = None
            var_match = re.search(r"([A-Z]\d+[A-Z0-9_]*)", ref_str)
            if var_match:
                ref_var = var_match.group(1)
            references.append(VariableReference(
                reference=ref_str,
                referenced_variable=ref_var,
            ))
            i += 1
            continue
        
        # Check for notes (asterisk)
        if line == "*":
            notes = "*"
            i += 1
            continue
        
        # Check for value code line
        # Pattern: frequency    code.  label (or code    label)
        # Examples:
        #   11490           010003-959738.  Household Identification Number
        #   9976           0.  Original sample household...
        #   232           5.  NO OTHER RESIDENCE
        # Pattern variations:
        #   - With frequency: "  11490           010003-959738.  Label"
        #   - Without frequency: "                         5.  NO OTHER RESIDENCE"
        #   - Blank: "             5       Blank.  Label"
        value_match = re.match(r"^\s*(\d+)?\s+([^\s.]+)(?:\.)?\s+(.+)$", line)
        if not value_match:
            # Try alternative pattern without frequency at start
            value_match = re.match(r"^\s+([^\s.]+)(?:\.)?\s+(.+)$", line)
            if value_match:
                freq_str = None
                code = value_match.group(1).strip()
                label = value_match.group(2).strip()
            else:
                i += 1
                continue
        else:
            freq_str = value_match.group(1)
            code = value_match.group(2).strip()
            label = value_match.group(3).strip()
        
        # Handle multi-line labels
        while i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if _is_separator(next_line) or re.match(r"^\s*\d+\s+", next_line):
                break
            if next_line.startswith("Section") or re.match(r"^[A-Z0-9_]+\s{2,}", next_line):
                break
            if not next_line:
                break
            # Continuation line
            label += " " + next_line
            i += 1
        
        frequency = int(freq_str) if freq_str else None
        is_missing = code.lower() in ["blank", "missing", "na", "n/a"]
        is_range = "-" in code and code.replace("-", "").replace(".", "").isdigit()
        
        value_codes.append(ValueCode(
            code=code,
            frequency=frequency,
            label=label,
            is_missing=is_missing,
            is_range=is_range,
        ))
        in_value_section = True
        i += 1
        continue
        
        # Skip dots line
        if line.startswith("." * 10):
            in_value_section = True
            i += 1
            continue
        
        # If we're in value section and hit empty line, might be end
        if in_value_section and not line:
            i += 1
            continue
        
        # Skip other lines
        i += 1
    
    return value_codes, assignments, references, notes


def _is_separator(line: str) -> bool:
    """Check if line is a separator (===)."""
    return line.strip().startswith("=" * 10)


def _is_variable_start(line: str) -> bool:
    """Check if line starts a variable definition."""
    return bool(re.match(r"^[A-Z0-9_]+\s{2,}", line.strip()))


def _is_identifier(var_name: str, description: str) -> bool:
    """Check if variable is an identifier."""
    id_keywords = ["IDENTIFICATION", "ID", "NUMBER", "HHID", "PN"]
    return any(keyword in description.upper() or keyword in var_name.upper() for keyword in id_keywords)
