"""This module contains functions to parse the codebooks for the imputation variables in the core files."""

import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import traceback
from typing import Dict, List, Optional, Tuple

from src.parse.parse_codebooks import find_imputations_codebook_files
from src.parse.parse_exit_codebook import _extract_year_from_path
from src.parse.parse_txt_codebook import (_extract_year_from_filename, _is_separator, _parse_level, _is_identifier, _is_variable_start)

# Type alias for (var_name, description, type_str, width, decimals, value_codes)
_ExitVarRow = Tuple[str, str, str, int, int, List[Tuple[str, Optional[str], Optional[int]]]]

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


def parse_core_imputations_codebook():
    return None


def parse_core_imputations_txt_codebook(
        txt_path: Path, 
        source: str = "hrs_core_imputations_codebook", 
        year: Optional[int] = None,
    ) -> Codebook:
    """Parse the core imputations codebook from a TXT file.
    
    Args:
        txt_path: Path to the TXT codebook file.
        source: Source identifier (e.g. 'hrs_core_imputations_codebook').
        year: Optional year; inferred from path if not set.
        
    Returns:
        Parsed Imputation Codebook.
    """
    if not txt_path.exists():
        raise FileNotFoundError(f"Codebook file not found: {txt_path}")
    
    #get year from filename if not provided
    if year is None:
        year = _extract_year_from_filename(txt_path)

    content = txt_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()

    #header
    release_type = _extract_release_type(content)

    # sections/variables
    sections: Dict[str, Section] = {}
    variables: List[Variable] = []
    current_section: Optional[Section] = None
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

        # Check for variable definition line
        var_match = re.match(r"^([A-Z0-9_]+)\s{2,}(.+)$", line)
        if var_match and current_section:
            var_name = var_match.group(1).strip()
            var_description = var_match.group(2).strip()
            metadata_line_idx = i + 1
        
            # Look for metadata line this codebook has metadata on two lines (e.g., "Type: Numeric, Width: 8, Decimals: 2")
            var_data = None
            if metadata_line_idx + 1 < len(lines):
                for offset in range(0, min(4, len(lines) - metadata_line_idx)):
                    candidate_idx = metadata_line_idx + offset
                    metadata_line1 = lines[candidate_idx].strip()
                    if not metadata_line1:
                        continue
                    metadata_line2 = lines[candidate_idx + 1].strip()
                    var_data = _parse_variable_metadata(metadata_line1, metadata_line2, var_name, var_description,
                                                       current_section, current_level, year)
                    if var_data:
                        metadata_line_idx = candidate_idx + 1
                        break
                    else:
                        var_data = None
            if var_data:
                # Skip variable name and description + metadata
                lines_to_skip = 2 + (metadata_line_idx - i)
                i += lines_to_skip
                # parse value codes and assignments
                value_codes, assignments, references, notes, i = _parse_variable_content(lines, i, var_data)
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


#maybe modify for imputations if needed
def _extract_release_type(content: str) -> Optional[str]:
    """Extract release type from header (e.g., 'Final Release')."""
    match = re.search(r"HRS\s+\d{4}\s+(.+?)\s*$", content[:500], re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None

def _parse_variable_metadata(metadata_line1: str, metadata_line2: str, var_name: str, var_description: str, section: str, level: VariableLevel, year: int,) -> Optional[Dict]:
    """Parse metadata lines for a variable in imputations codebook. the metadata is over two lines """
    # Extract section from line if present (modern format)
    section_match = re.search(r"[Ss]ection:\s*([A-Z]+)", metadata_line1)
    use_section = section_match.group(1) if section_match else section
    
    # Legacy: require at least Type: or Width: to consider this a metadata line
    type_match = re.search(r"Type:\s*(\w+)", metadata_line2)
    width_match = re.search(r"Width:\s*(\d+)", metadata_line2)
    if not type_match and not width_match:
        return None
    
    # Extract level
    level_match = re.search(r"Level:\s*([^T]+?)(?:\s+Type:|$)", metadata_line1)
    level_str = level_match.group(1).strip() if level_match else str(level.value)
    parsed_level = _parse_level(level_str)
    
    var_type = VariableType.CHARACTER
    if type_match:
        type_str = type_match.group(1).strip()
        var_type = VariableType.CHARACTER if "Character" in type_str else VariableType.NUMERIC
    
    width = int(width_match.group(1)) if width_match else 0
    
    decimals_match = re.search(r"Decimals:\s*(\d+)", metadata_line2)
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
    """Parse value codes and user notes for a variable (for core imputations)"""
    value_codes: List[ValueCode] = []
    assignments: List[VariableAssignment] = []
    references: List[VariableReference] = []
    notes: Optional[str] = None
    
    i = start_idx
    in_value_section = False
    current_label_lines: List[str] = []
    
    line = lines[i].strip()
    match_user_notes = re.match(r"(?i)^User\s+Note:\s*(.+)$", line)
    if match_user_notes:
        notes = match_user_notes.group(1).strip()
        # multi-line notes
        while i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if not next_line or next_line.startswith("."):
                break
            notes += " " + next_line
            i += 1
        i += 1
    while i < len(lines):
        line = lines[i].strip()
        
        
        
        
        line = lines[i].strip()
        # Stop at separator or next variable/section
        section_match = re.match(
            r"(?i)^section\s+([A-Z]+):\s+(.+?)(?:\s+\((.+?)\))?\s*$", line
        )
        if section_match:
            i-=1
            break


        if _is_separator(line):
            break
        
        
        
        
        
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
        value_match = re.match(r"^\s*(\d+)?\s+([^\s.]+)(?:\.)\s+(.+)$", line)
        if not value_match:
            # Try alternative pattern without frequency at start
            value_match = re.match(r"^\s+([^\s.]+)(?:\.)\s+(.+)$", line)
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
            if next_line.startswith("..."):
                break
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
    
    return value_codes, assignments, references, notes, i

def main() -> None:
    """CLI: parse core imputation codebooks and save to JSON."""
    import argparse
    import sys

    from .save_codebook import save_core_imputations_codebook_json

    parser = argparse.ArgumentParser(description="Parse core imputation codebooks and save to JSON.")

    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory containing HRS Data folder",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data") / "parsed",
        help="Output directory for parsed JSON",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=None,
        help="Process only this year (default: all years under data-dir)",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="hrs_core_imputations_codebook",
        help="Source identifier",
    )
    args = parser.parse_args()

    print(f"Finding core imputation codebooks in {args.data_dir}...")

    files = find_imputations_codebook_files(args.data_dir, args.year, type="Core")
    if not files:
        print("No core imputation codebook files found.")
        sys.exit(1)

    # Group by year for merge  (year from filename or from path)
    files_by_year: Dict[int, List[Path]] = {}
    for p in files:
        y = _extract_year_from_path(p)
        if y is not None:
            #find year folder
            parent = p.parent
            while parent != parent.parent:
                if parent.name.isdigit() and len(parent.name) == 4:
                    try:
                        yi = int(parent.name)
                        if 1990 <= yi <= 2030:
                            y = yi
                            break
                    except ValueError:
                        pass
                parent = parent.parent
        if y is not None:
            files_by_year.setdefault(y, []).append(p)
    for y, paths in sorted(files_by_year.items()):
        try:
            if len(paths) >= 1:
                print(f"Parsing {paths[0]}")
                codebook = parse_core_imputations_txt_codebook(paths[0], source=args.source, year=y)
            else:
                print(f"No codebook file found for year {y}")
                continue
            out = save_core_imputations_codebook_json(codebook, args.output_dir, pretty=True)
            print(f"Saved {codebook.total_variables} variables, {codebook.total_sections} sections -> {out}")
        except Exception as e:
            print(f" ERROR: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)
    print("Done.")


if __name__ == "__main__":
    main()
