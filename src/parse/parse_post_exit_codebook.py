"""Parse HRS post-exit codebook files (.txt) into ExitCodebook models.

Follows config/sources.yaml (hrs_post_exit_codebook) and data layout:
  data/HRS Data/{year}/Post Exit/  with .txt files (e.g. PX22cb/PX2022cb.txt).

Post-exit .txt format:
  - Section header: "Section PR: PRELOAD  (Respondent)" or "(HH Member Child)"
  - Variable block: "VARNAME                          DESCRIPTION" then
    "         Section: PR    Level: Respondent      Type: Character  Width: 6   Decimals: 0"
    optional "Ref:" and description lines, "         ........." then value code lines
  - Value codes: "           109           1.  LABEL" or "                     Blank.  Data Missing"
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.models.exits import (
    ExitCodebook,
    ExitSection,
    ExitVariable,
    ExitVariableLevel,
    ExitVariableType,
    ExitValueCode,
)

from .parse_exit_codebook import _extract_year_from_path


POST_EXIT_SOURCE = "hrs_post_exit_codebook"

# Variable name at start of line (optional leading spaces), then 2+ spaces, then description
_RE_VAR_LINE = re.compile(r"^\s*([A-Z0-9_]+)\s{2,}(.+)$", re.IGNORECASE)
# Section header: Section CODE: NAME  (Level)
_RE_SECTION = re.compile(r"(?i)^section\s+([A-Z]+):\s+(.+?)\s+\((.+)\)\s*$")
# Metadata: Section: PR    Level: Respondent      Type: Character  Width: 6   Decimals: 0
_RE_META = re.compile(
    r"(?i).*Section:\s*([A-Z]+)\s+Level:\s*(.+?)\s+Type:\s*(\w+)\s+Width:\s*(\d+)\s+Decimals:\s*(\d+)",
    re.DOTALL,
)
# Value code: optional frequency, then code (may end with .), then label. Allow "Blank.  Data Missing"
_RE_VALUE_LINE = re.compile(r"^\s*(\d+)?\s*([^\s]+?)(?:\.)?\s{2,}(.+)$")


def _parse_level_post_exit(s: str) -> ExitVariableLevel:
    s = (s or "").strip().lower()
    if "household" in s and "child" not in s:
        return ExitVariableLevel.HOUSEHOLD
    if "respondent" in s or s == "r":
        return ExitVariableLevel.RESPONDENT
    if "child" in s or "member" in s or "hh member" in s:
        return ExitVariableLevel.OTHER
    return ExitVariableLevel.RESPONDENT


def _parse_type_post_exit(s: str) -> ExitVariableType:
    s = (s or "").strip().lower()
    if "numeric" in s or "num" in s:
        return ExitVariableType.NUMERIC
    return ExitVariableType.CHARACTER


def _parse_metadata_line(line: str) -> Optional[Dict]:
    """Extract Section, Level, Type, Width, Decimals from metadata line."""
    m = _RE_META.search(line)
    if not m:
        return None
    section_code = m.group(1).strip()
    level_str = m.group(2).strip()
    type_str = m.group(3).strip()
    width = int(m.group(4))
    decimals = int(m.group(5))
    return {
        "section": section_code,
        "level": _parse_level_post_exit(level_str),
        "type": _parse_type_post_exit(type_str),
        "width": width,
        "decimals": decimals,
    }


def _parse_value_codes_post_exit(lines: List[str], start: int) -> Tuple[List[ExitValueCode], int]:
    """Parse value code lines until separator or next variable. Returns (codes, next_line_index)."""
    out: List[ExitValueCode] = []
    i = start
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        # Stop at separator or section or new variable
        if re.match(r"^=+\s*$", line):
            return out, i
        if re.match(r"(?i)^section\s+[A-Z]+:", line):
            return out, i
        # Don't treat "  109  013137-907335.  Label" as variable (frequency then code)
        var_match = _RE_VAR_LINE.match(raw)
        if var_match and not line.startswith(".") and not var_match.group(1).isdigit():
            return out, i
        # Skip metadata line (Section: ... Level: ... Type: ...), dots, Ref:, ASSIGN:, empty
        if _parse_metadata_line(raw) is not None:
            i += 1
            continue
        if not line or line.startswith(".") or line.startswith("Ref:") or line.startswith("ASSIGN:"):
            i += 1
            continue
        m = _RE_VALUE_LINE.match(raw)
        if m:
            freq = int(m.group(1)) if m.group(1) else None
            code = m.group(2).strip()
            label = m.group(3).strip()
            i += 1
            # Continuation lines for label (no leading number/code)
            while i < len(lines):
                next_ln = lines[i]
                next_stripped = next_ln.strip()
                if not next_stripped:
                    break
                if re.match(r"^=+\s*$", next_stripped):
                    break
                if _RE_VALUE_LINE.match(next_ln) or _RE_VAR_LINE.match(next_ln):
                    break
                if next_stripped.startswith("Section ") and ":" in next_stripped:
                    break
                label += " " + next_stripped
                i += 1
            is_missing = code.lower() in ("blank", "missing", "na", "inap", "dk", "rf")
            out.append(
                ExitValueCode(code=code, frequency=freq, label=label or None, is_missing=is_missing)
            )
        else:
            i += 1
    return out, i


def _section_key(code: str, level: ExitVariableLevel) -> Tuple[str, str]:
    return (code, level.value)


def parse_post_exit_txt_codebook(
    txt_path: Path,
    source: str = POST_EXIT_SOURCE,
    year: Optional[int] = None,
) -> ExitCodebook:
    """Parse a post-exit codebook .txt file (HRS Post Exit format)."""
    if not txt_path.exists():
        raise FileNotFoundError(f"Post-exit codebook file not found: {txt_path}")
    if year is None:
        year = _extract_year_from_path(txt_path)
    if year is None:
        for part in txt_path.parts:
            if part.isdigit() and len(part) == 4 and 1990 <= int(part) <= 2030:
                year = int(part)
                break
    if year is None:
        raise ValueError(f"Cannot determine year from path: {txt_path}")

    content = txt_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()
    sections: Dict[Tuple[str, str], ExitSection] = {}
    variables: List[ExitVariable] = []
    current_section: Optional[str] = None
    current_section_name: Optional[str] = None
    current_level: ExitVariableLevel = ExitVariableLevel.RESPONDENT
    i = 0

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        # Section header: Section PR: PRELOAD  (Respondent)
        sec_match = _RE_SECTION.match(line)
        if sec_match:
            current_section = sec_match.group(1)
            current_section_name = sec_match.group(2).strip()
            current_level = _parse_level_post_exit(sec_match.group(3))
            key = _section_key(current_section, current_level)
            if key not in sections:
                sections[key] = ExitSection(
                    code=current_section,
                    name=current_section_name,
                    level=current_level,
                    year=year,
                    variable_count=0,
                    variables=[],
                )
            i += 1
            continue

        # Variable name line: VARNAME   spaces   DESCRIPTION (allow leading spaces in raw line)
        var_match = _RE_VAR_LINE.match(raw)
        if var_match and current_section:
            var_name = var_match.group(1).strip()
            var_desc = var_match.group(2).strip()
            # Skip ASSIGN/dash separator and value-code lines misread as variable (e.g. "  109  ...")
            if var_name.startswith("-") or "ASSIGN" in line.upper() or var_name.isdigit():
                i += 1
                continue
            meta_idx = i + 1
            meta_dict = None
            for off in range(min(8, len(lines) - meta_idx)):
                cand = lines[meta_idx + off].strip()
                if not cand:
                    continue
                meta_dict = _parse_metadata_line(cand)
                if meta_dict:
                    meta_idx = meta_idx + off
                    break
            if meta_dict:
                value_codes, next_i = _parse_value_codes_post_exit(lines, meta_idx + 1)
                var = ExitVariable(
                    name=var_name,
                    year=year,
                    section=meta_dict["section"],
                    level=meta_dict["level"],
                    description=var_desc or var_name,
                    type=meta_dict["type"],
                    width=meta_dict["width"],
                    decimals=meta_dict["decimals"],
                    value_codes=value_codes,
                    has_value_codes=len(value_codes) > 0,
                )
                variables.append(var)
                # Add to section that matches variable's section+level
                sk = _section_key(meta_dict["section"], meta_dict["level"])
                if sk in sections:
                    sections[sk].variables.append(var_name)
                    sections[sk].variable_count += 1
                else:
                    # Create section if we saw variable before its header (shouldn't happen in order)
                    sections[sk] = ExitSection(
                        code=meta_dict["section"],
                        name=current_section_name or meta_dict["section"],
                        level=meta_dict["level"],
                        year=year,
                        variable_count=1,
                        variables=[var_name],
                    )
                i = next_i
                while i < len(lines):
                    ln = lines[i].strip()
                    if re.match(r"^=+\s*$", ln):
                        i += 1
                        break
                    if _RE_VAR_LINE.match(lines[i]) and not ln.startswith("-"):
                        break
                    i += 1
                continue
        i += 1

    for s in sections.values():
        s.variable_count = len(s.variables)
    levels = {v.level for v in variables}
    release_type = None
    if "Post Exit" in content[:3000] and "Final" in content[:3000]:
        release_type = "Final Post Exit"

    return ExitCodebook(
        source=source,
        year=year,
        release_type=release_type,
        sections=list(sections.values()),
        variables=variables,
        total_variables=len(variables),
        total_sections=len(sections),
        levels=levels,
        metadata={"file_path": str(txt_path), "file_name": txt_path.name},
        parsed_at=datetime.now(),
    )


def parse_post_exit_codebook(
    file_path: Path,
    source: str = POST_EXIT_SOURCE,
    year: Optional[int] = None,
) -> ExitCodebook:
    """Parse a post-exit codebook file (.txt) into an ExitCodebook model."""
    if not file_path.exists():
        raise FileNotFoundError(f"Post-exit codebook file not found: {file_path}")

    if year is None:
        year = _extract_year_from_path(file_path)
    if year is None:
        stem = file_path.stem
        px_match = re.search(r"px(\d{2,4})", stem, re.I)
        if px_match:
            yy = int(px_match.group(1))
            if 1990 <= yy <= 2030:
                year = yy
            elif yy >= 90:
                year = 1900 + yy
            else:
                year = 2000 + yy
            if year < 1990 or year > 2030:
                year = None
    if year is None:
        for part in file_path.parts:
            if part.isdigit() and len(part) == 4 and 1990 <= int(part) <= 2030:
                year = int(part)
                break
    if year is None:
        raise ValueError(f"Cannot determine year from path: {file_path}")

    return parse_post_exit_txt_codebook(file_path, source=source, year=year)


def _is_main_post_exit_codebook(path: Path, year: int) -> bool:
    """Prefer one main combined codebook per year (e.g. PX2022cb.txt, px2016cb.txt)."""
    stem = path.stem
    yy = year % 100
    # Prefer PX{year}cb or px{year}cb (4-digit) or PX{yy}cb / px{yy}cb when it's the only cb file
    if re.match(rf"(?i)px{year}cb$", stem):
        return True
    if re.match(rf"(?i)px{yy:02d}cb$", stem):
        return True
    return False


def find_post_exit_codebook_files(
    data_dir: Path,
    year: Optional[int] = None,
) -> List[Path]:
    """Find one main post-exit codebook file per year (e.g. PX2022cb.txt)."""
    from src.config_loader import get_years_for_source

    base = data_dir.resolve()
    years = get_years_for_source(POST_EXIT_SOURCE)
    if year is not None:
        years = [y for y in years if y == year]
    codebooks: List[Path] = []
    for y in years:
        yy = y % 100
        post_exit_dir = base / "HRS Data" / str(y) / "Post Exit"
        if not post_exit_dir.exists():
            continue
        all_txt: List[Path] = []
        for subdir_name in (
            f"px{yy:02d}cb", f"px{yy:02d}pr", f"px{y}cb", f"px{y}pr",
            f"PX{yy:02d}cb", f"PX{y}cb",
        ):
            subdir = post_exit_dir / subdir_name
            if subdir.exists():
                all_txt = [f for f in subdir.glob("*.txt") if f.is_file()]
                break
        if not all_txt:
            all_txt = [f for f in post_exit_dir.glob("*.txt") if f.is_file()]
        # Prefer main combined codebook (PX2022cb, px2016cb, px00cb, etc.)
        main = [f for f in all_txt if _is_main_post_exit_codebook(f, y)]
        if main:
            codebooks.append(main[0])
        elif all_txt:
            codebooks.append(sorted(all_txt)[0])
    return sorted(set(codebooks))
