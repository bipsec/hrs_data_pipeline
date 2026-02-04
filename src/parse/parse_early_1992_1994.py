"""Parse 1992 and 1994 HRS core codebook .TXT files (multi-file, section-per-file layout)."""

import re
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime

from src.models.cores import (
    Variable,
    ValueCode,
    Section,
    VariableLevel,
    VariableType,
    CodebookLegacy,
    CoreDataPeriod,
    get_wave_number,
)


def _section_code_from_filename(path: Path) -> str:
    """Derive section code from filename: 04_0.TXT -> 0, 05_A.txt -> A, 02_W2CS.TXT -> W2CS."""
    stem = path.stem.upper()
    if "_" in stem:
        parts = stem.split("_", 1)
        return parts[1] if len(parts) > 1 else stem
    return stem


def _parse_section_header(content: str) -> Optional[Tuple[str, str]]:
    """Parse 'Section 0: Face Sheet...' or 'Section A: Demographic Background'. Returns (code, name)."""
    # Section 0: ... or Section A: ...
    m = re.search(r"[Ss]ection\s+([A-Z0-9]+):\s*(.+?)(?=\s*_{5,}|$)", content[:2000], re.DOTALL)
    if m:
        code = m.group(1).strip()
        name = m.group(2).strip().replace("\n", " ").strip()
        return (code, name)
    # Coversheets: Household and Individual (1994)
    m = re.search(r"^\s*([A-Za-z][A-Za-z0-9\s]*):\s*(.+?)(?=\s*_{5,}|$)", content[:1500], re.MULTILINE)
    if m:
        name = f"{m.group(1).strip()}: {m.group(2).strip()}"
        return ("CS", name[:80])
    return None


def _variable_line_1992(line: str) -> Optional[Tuple[str, str]]:
    """1992: '        21      FACESHEET: Interviewer ID' -> (V21, description)."""
    m = re.match(r"^\s*(\d+)\s{2,}(.+)$", line)
    if not m:
        return None
    num = m.group(1)
    desc = m.group(2).strip()
    if re.match(r"^V\d+\s+Code", desc) or re.search(r"Variable\s+N\s+Mean", desc):
        return None
    return (f"V{num}", desc)


def _variable_line_1994(line: str) -> Optional[Tuple[str, str]]:
    """1994: 'HHID    HHID    HRS Household Identifier' or '        W100    HHCS5.  ...'."""
    # NAME    NAME    Description or NAME    Description
    m = re.match(r"^\s*([A-Z0-9]+)\s{2,}(.+)$", line)
    if not m:
        return None
    name = m.group(1)
    rest = m.group(2).strip()
    if name.upper().startswith("V") and name[1:].isdigit() and ("Code" in rest or "Frequency" in rest):
        return None
    if re.search(r"Variable\s+", rest) or "Code Frequency" in rest:
        return None
    # If rest looks like duplicate name then description (HHID    HHID    Desc)
    parts = rest.split(None, 1)
    if len(parts) >= 2 and parts[0] == name:
        desc = parts[1]
    else:
        desc = rest
    return (name, desc)


def _value_code_line(line: str) -> Optional[Tuple[Optional[int], str, str]]:
    """Parse value line: '        9999.   NA' or '                   1.      Yes' -> (freq, code, label)."""
    # Optional frequency, then code (digits/dots/Blank etc), then period, then label
    m = re.match(r"^\s*(\d+)\s+(\d+)\s*\.\s+(.+)$", line)
    if m:
        return (int(m.group(1)), m.group(2), m.group(3).strip())
    m = re.match(r"^\s*(\d+)\s*\.\s+(.+)$", line)
    if m:
        return (None, m.group(1), m.group(2).strip())
    m = re.match(r"^\s*([A-Za-z]+)\s*\.\s+(.+)$", line)
    if m:
        return (None, m.group(1), m.group(2).strip())
    # "        1       3178" frequency line (code then freq)
    m = re.match(r"^\s*(\d+)\s+(\d+)\s*$", line)
    if m:
        return (int(m.group(2)), m.group(1), "")
    return None


def parse_early_codebook_file(
    txt_path: Path,
    year: int,
    source: str,
    section_code_override: Optional[str] = None,
) -> Tuple[List[Section], List[Variable]]:
    """Parse one 1992 or 1994 section .TXT file; return (sections, variables)."""
    if not txt_path.exists():
        raise FileNotFoundError(f"Codebook file not found: {txt_path}")
    content = txt_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()
    section_code = section_code_override or _section_code_from_filename(txt_path)
    section_header = _parse_section_header(content)
    if section_header:
        section_code, section_name = section_header
    else:
        section_name = f"Section {section_code}"
    section = Section(
        code=section_code,
        name=section_name,
        level=VariableLevel.RESPONDENT,
        year=year,
    )
    sections = [section]
    variables: List[Variable] = []
    is_1992 = year == 1992
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if re.match(r"VAR\s*#|_____|Variable\s+N\s+Mean|Code\s+Frequency", stripped, re.IGNORECASE):
            i += 1
            continue
        var_info = _variable_line_1992(stripped) if is_1992 else _variable_line_1994(stripped)
        if not var_info:
            i += 1
            continue
        var_name, var_description = var_info
        value_codes: List[ValueCode] = []
        j = i + 1
        while j < len(lines):
            next_ln = lines[j]
            next_stripped = next_ln.strip()
            if not next_stripped:
                j += 1
                continue
            if re.match(r"^\s*\d+\s{2,}[A-Z]", next_stripped) or re.match(
                r"^\s*[A-Z0-9]+\s{2,}.+", next_stripped
            ):
                if _variable_line_1992(next_stripped) if is_1992 else _variable_line_1994(next_stripped):
                    break
            if re.match(r"^_{10,}", next_stripped) or re.match(r"^\.{10,}", next_stripped):
                j += 1
                continue
            vc = _value_code_line(next_stripped)
            if vc:
                freq, code, label = vc
                if code or label:
                    value_codes.append(
                        ValueCode(
                            code=code,
                            frequency=freq,
                            label=label if label else None,
                            is_missing=code.upper() in ("BLANK", "NA", "DK", "INAP"),
                            is_range=False,
                        )
                    )
            elif "Variable   N" in next_stripped or "Code Frequency" in next_stripped or "Code  Frequency" in next_stripped:
                pass
            elif re.match(r"^\s*\d+\s+\d+\s*$", next_stripped):
                fc = _value_code_line(next_stripped)
                if fc and fc[2] == "" and fc[1]:
                    value_codes.append(
                        ValueCode(code=fc[1], frequency=fc[0], label=None, is_missing=False, is_range=False)
                    )
            j += 1
        variable = Variable(
            name=var_name,
            year=year,
            section=section_code,
            level=VariableLevel.RESPONDENT,
            description=var_description[:500] if len(var_description) > 500 else var_description,
            type=VariableType.NUMERIC if var_name.upper().startswith("V") and var_name[1:].isdigit() else VariableType.CHARACTER,
            width=0,
            decimals=0,
            value_codes=value_codes,
            has_value_codes=len(value_codes) > 0,
            is_identifier=any(x in var_name.upper() for x in ("HHID", "PN", "ID")),
        )
        variables.append(variable)
        section.variables.append(var_name)
        i = j
    section.variable_count = len(section.variables)
    return (sections, variables)


def parse_and_merge_early_codebook(
    file_paths: List[Path],
    year: int,
    source: str = "hrs_core_codebook",
) -> CodebookLegacy:
    """Parse multiple 1992/1994 section files and merge into one CodebookLegacy."""
    all_sections: List[Section] = []
    all_variables: List[Variable] = []
    for path in sorted(file_paths):
        sections, variables = parse_early_codebook_file(path, year=year, source=source)
        all_sections.extend(sections)
        all_variables.extend(variables)
    levels = {VariableLevel.RESPONDENT}
    return CodebookLegacy(
        source=source,
        year=year,
        release_type=None,
        wave=get_wave_number(year),
        core_period=CoreDataPeriod.LEGACY,
        sections=all_sections,
        variables=all_variables,
        total_variables=len(all_variables),
        total_sections=len(all_sections),
        levels=levels,
        metadata={"file_paths": [str(p) for p in file_paths], "early_format": True},
        parsed_at=datetime.now(),
    )
