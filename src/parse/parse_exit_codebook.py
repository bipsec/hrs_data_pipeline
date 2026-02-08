"""Parse HRS exit codebook files (HTML or TXT) into ExitCodebook models."""

import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Type alias for (var_name, description, type_str, width, decimals, value_codes)
_ExitVarRow = Tuple[str, str, str, int, int, List[Tuple[str, Optional[str], Optional[int]]]]

from src.models.exits import (
    ExitCodebook,
    ExitSection,
    ExitVariable,
    ExitVariableLevel,
    ExitVariableType,
    ExitValueCode,
)


def _extract_year_from_path(path: Path) -> Optional[int]:
    """Extract year from path or filename (e.g. x95cb -> 1995, x96... -> 1996, x2020cb -> 2020)."""
    stem = path.stem
    m = re.search(r"(?:h|x)(\d{2,4})", stem, re.I)
    if m:
        y = int(m.group(1))
        if y < 100:
            if y == 95:
                return 1995
            return 1996 + (y - 96) // 2 * 2 if y >= 96 else None
        if 1990 <= y <= 2030:
            return y
    for part in path.parts:
        if part.isdigit() and len(part) == 4 and 1990 <= int(part) <= 2030:
            return int(part)
    return None


def _parse_level(s: str) -> ExitVariableLevel:
    s = (s or "").strip().lower()
    if "household" in s or "hh" in s:
        return ExitVariableLevel.HOUSEHOLD
    if "respondent" in s or "resp" in s or "r" == s:
        return ExitVariableLevel.RESPONDENT
    return ExitVariableLevel.RESPONDENT


def _parse_type(s: str) -> ExitVariableType:
    s = (s or "").strip().lower()
    if "num" in s or "int" in s or "float" in s:
        return ExitVariableType.NUMERIC
    return ExitVariableType.CHARACTER


class _ExitHtmlParser(HTMLParser):
    """Extract variable-like rows from exit codebook HTML (tables and text)."""

    def __init__(self) -> None:
        super().__init__()
        self.variables: List[_ExitVarRow] = []
        self._current_var: Optional[_ExitVarRow] = None
        self._in_table = False
        self._in_cell = False
        self._cell_data: List[str] = []
        self._row_cells: List[str] = []
        self._current_section = "Exit"
        self._var_name_re = re.compile(r"^[A-Z][A-Z0-9_]{1,32}$")

    def handle_starttag(self, tag: str, attrs: list) -> None:
        attrs_d = dict(attrs)
        if tag == "table":
            self._in_table = True
            self._row_cells = []
        elif tag in ("td", "th"):
            self._in_cell = True
            self._cell_data = []

    def handle_endtag(self, tag: str) -> None:
        if tag in ("td", "th"):
            self._in_cell = False
            self._row_cells.append(" ".join(self._cell_data).strip())
        elif tag == "tr" and self._row_cells:
            self._process_row(self._row_cells)
            self._row_cells = []
        elif tag == "table":
            self._in_table = False

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_data.append(data.strip())

    def _process_row(self, cells: List[str]) -> None:
        if len(cells) < 2:
            return
        first = (cells[0] or "").strip()
        if not first:
            return
        # Variable name in first column (e.g. EEXDATE, REXDATE)
        if self._var_name_re.match(first):
            var_name = first
            desc = (cells[1] if len(cells) > 1 else "").strip()
            type_str = (cells[2] if len(cells) > 2 else "").strip()
            width = 0
            try:
                if len(cells) > 3 and cells[3].strip().isdigit():
                    width = int(cells[3].strip())
            except ValueError:
                pass
            value_codes: List[Tuple[str, Optional[str], Optional[int]]] = []
            self.variables.append((var_name, desc, type_str, width, 0, value_codes))
            self._current_var = self.variables[-1]
        # Value code row: code, label, frequency (attach to last variable)
        elif self._current_var and len(cells) >= 2:
            code = (cells[0] or "").strip()
            label = (cells[1] if len(cells) > 1 else "").strip() or None
            freq: Optional[int] = None
            if len(cells) > 2 and (cells[2] or "").strip().replace(",", "").isdigit():
                try:
                    freq = int((cells[2] or "").strip().replace(",", ""))
                except ValueError:
                    pass
            if code or label:
                self._current_var[5].append((code or "", label, freq))

    def _fix_current_var(self) -> None:
        if self.variables:
            self._current_var = self.variables[-1]


def _parse_html_tables(html_content: str) -> List[_ExitVarRow]:
    """Parse HTML and return list of (var_name, description, type_str, width, decimals, value_codes)."""
    p = _ExitHtmlParser()
    p.feed(html_content)
    return p.variables


def _parse_html_fallback(html_content: str) -> List[_ExitVarRow]:
    """Fallback: find variable-like names and descriptions with regex."""
    variables: List[_ExitVarRow] = []
    var_re = re.compile(r"\b([A-Z][A-Z0-9_]{2,32})\s*[-–:]?\s*(.+?)(?=\s{2,}[A-Z][A-Z0-9_]{2,}|\n\n|$)", re.S)
    for m in var_re.finditer(html_content):
        name = m.group(1).strip()
        rest = m.group(2).strip()
        if name in ("HTML", "HTTP", "PDF", "DOC"):
            continue
        desc = rest.split("\n")[0].strip()[:500]
        variables.append((name, desc, "Character", 0, 0, []))
    return variables


def parse_exit_codebook(
    html_path: Path,
    source: str = "hrs_exit_codebook",
    year: Optional[int] = None,
) -> ExitCodebook:
    """Parse an exit codebook file (HTML or TXT) into an ExitCodebook model.

    For .txt files uses the same format as core (Section X: Name (Level), variables, value codes).
    For .htm/.html uses table-based HTML parsing.

    Args:
        html_path: Path to the codebook file (.txt or .htm/.html).
        source: Source identifier from config (default hrs_exit_codebook).
        year: Survey year; inferred from path/filename if not provided.

    Returns:
        ExitCodebook with variables and sections.
    """
    if not html_path.exists():
        raise FileNotFoundError(f"Exit codebook file not found: {html_path}")

    if year is None:
        year = _extract_year_from_path(html_path)
    if year is None:
        raise ValueError(f"Cannot determine year from path: {html_path}")

    if html_path.suffix.lower() == ".txt":
        return parse_exit_txt_codebook(html_path, source=source, year=year)

    content = html_path.read_text(encoding="utf-8", errors="ignore")
    # Normalize and strip script/style to reduce noise
    content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.S | re.I)
    content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.S | re.I)

    variables_tuples = _parse_html_tables(content)
    if not variables_tuples:
        variables_tuples = _parse_html_fallback(content)

    variables: List[ExitVariable] = []
    section_var_names: List[str] = []
    for var_name, desc, type_str, width, decimals, value_code_tuples in variables_tuples:
        level = ExitVariableLevel.RESPONDENT
        value_codes = [
            ExitValueCode(code=c, label=l, frequency=f)
            for c, l, f in value_code_tuples
        ]
        v = ExitVariable(
            name=var_name,
            year=year,
            section="Exit",
            level=level,
            description=desc or var_name,
            type=_parse_type(type_str),
            width=width,
            decimals=decimals,
            value_codes=value_codes,
            has_value_codes=len(value_codes) > 0,
        )
        variables.append(v)
        section_var_names.append(var_name)

    section = ExitSection(
        code="EX",
        name="Exit",
        level=ExitVariableLevel.RESPONDENT,
        year=year,
        variable_count=len(variables),
        variables=section_var_names,
    )
    levels = {ExitVariableLevel.RESPONDENT}
    for v in variables:
        levels.add(v.level)

    return ExitCodebook(
        source=source,
        year=year,
        sections=[section],
        variables=variables,
        total_variables=len(variables),
        total_sections=1,
        levels=levels,
        metadata={"file_path": str(html_path), "file_name": html_path.name},
    )


def _exit_txt_parse_metadata(
    line: str, section: str, level: ExitVariableLevel, year: int
) -> Optional[Dict]:
    """Parse a variable metadata line; return dict for ExitVariable or None."""
    if not re.search(r"Type:\s*\w+", line) and not re.search(r"Width:\s*\d+", line):
        return None
    sec_m = re.search(r"[Ss]ection:\s*([A-Z]+)", line)
    use_section = sec_m.group(1) if sec_m else section
    level_m = re.search(r"Level:\s*([^T]+?)(?:\s+Type:|$)", line)
    level_str = level_m.group(1).strip() if level_m else level.value
    type_m = re.search(r"Type:\s*(\w+)", line)
    width_m = re.search(r"Width:\s*(\d+)", line)
    dec_m = re.search(r"Decimals:\s*(\d+)", line)
    var_type = ExitVariableType.NUMERIC if type_m and "Numeric" in (type_m.group(1) or "") else ExitVariableType.CHARACTER
    width = int(width_m.group(1)) if width_m else 0
    decimals = int(dec_m.group(1)) if dec_m else 0
    return {
        "section": use_section,
        "level": _parse_level(level_str),
        "type": var_type,
        "width": width,
        "decimals": decimals,
    }


def _exit_txt_parse_value_codes(lines: List[str], start: int) -> Tuple[List[ExitValueCode], int]:
    """Parse value code lines until separator or next variable. Returns (codes, next_line_index)."""
    out: List[ExitValueCode] = []
    i = start
    while i < len(lines):
        line = lines[i].strip()
        if re.match(r"^=+\s*$", line) or (line.startswith("Section ") and ":" in line):
            return out, i
        if re.match(r"^[A-Z0-9_]+\s{2,}", line):
            return out, i
        m = re.match(r"^\s*(\d+)?\s+([^\s.]+)(?:\.)?\s+(.+)$", line)
        if m:
            freq = int(m.group(1)) if m.group(1) else None
            code = m.group(2).strip()
            label = m.group(3).strip()
            i += 1
            while i < len(lines):
                next_ln = lines[i].strip()
                if not next_ln or re.match(r"^\s*\d+\s+", next_ln) or next_ln.startswith("=") or re.match(r"^[A-Z0-9_]+\s{2,}", next_ln):
                    break
                label += " " + next_ln
                i += 1
            out.append(ExitValueCode(code=code, frequency=freq, label=label, is_missing=code.lower() in ("blank", "missing", "na")))
        else:
            i += 1
    return out, i


def parse_exit_txt_codebook(
    txt_path: Path,
    source: str = "hrs_exit_codebook",
    year: Optional[int] = None,
) -> ExitCodebook:
    """Parse an exit codebook .txt file (same layout as core: sections, variables, value codes)."""
    if not txt_path.exists():
        raise FileNotFoundError(f"Exit codebook file not found: {txt_path}")
    if year is None:
        year = _extract_year_from_path(txt_path)
    if year is None:
        raise ValueError(f"Cannot determine year from path: {txt_path}")
    content = txt_path.read_text(encoding="utf-8", errors="ignore")
    lines = content.splitlines()
    sections: Dict[str, ExitSection] = {}
    variables: List[ExitVariable] = []
    current_section: Optional[str] = None
    current_section_name: Optional[str] = None
    current_level: ExitVariableLevel = ExitVariableLevel.RESPONDENT
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        sec_match = re.match(r"(?i)^section\s+([A-Z]+):\s+(.+?)(?:\s+\((.+?)\))?\s*$", line)
        if sec_match:
            current_section = sec_match.group(1)
            current_section_name = sec_match.group(2).strip()
            current_level = _parse_level(sec_match.group(3).strip() if sec_match.group(3) else "Respondent")
            if current_section not in sections:
                sections[current_section] = ExitSection(
                    code=current_section,
                    name=current_section_name,
                    level=current_level,
                    year=year,
                    variable_count=0,
                    variables=[],
                )
            i += 1
            continue
        var_match = re.match(r"^([A-Z0-9_]+)\s{2,}(.+)$", line)
        var_name_only = re.match(r"^([A-Z0-9_]+)\s*$", line) and current_section
        if (var_match or var_name_only) and current_section:
            var_name = (var_match.group(1) if var_match else line).strip()
            var_desc = (var_match.group(2).strip() if var_match else var_name)
            meta_idx = i + 1
            meta_dict = None
            for off in range(min(4, len(lines) - meta_idx)):
                cand = lines[meta_idx + off].strip()
                if not cand:
                    continue
                meta_dict = _exit_txt_parse_metadata(cand, current_section, current_level, year)
                if meta_dict:
                    meta_idx = meta_idx + off
                    break
            if meta_dict:
                value_codes, next_i = _exit_txt_parse_value_codes(lines, meta_idx + 1)
                var = ExitVariable(
                    name=var_name,
                    year=year,
                    section=meta_dict["section"],
                    level=meta_dict["level"],
                    description=var_desc,
                    type=meta_dict["type"],
                    width=meta_dict["width"],
                    decimals=meta_dict["decimals"],
                    value_codes=value_codes,
                    has_value_codes=len(value_codes) > 0,
                )
                variables.append(var)
                sections[current_section].variables.append(var_name)
                sections[current_section].variable_count += 1
                i = next_i
                while i < len(lines) and not re.match(r"^=+\s*$", lines[i]) and not re.match(r"^[A-Z0-9_]+\s{2,}", lines[i].strip()):
                    i += 1
                continue
        i += 1
    for s in sections.values():
        s.variable_count = len(s.variables)
    levels = {v.level for v in variables}
    release_type = None
    if "Final Exit" in content[:2000]:
        release_type = "Final Exit"
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


def parse_and_merge_exit_codebook(
    paths: List[Path],
    year: int,
    source: str = "hrs_exit_codebook",
) -> ExitCodebook:
    """Parse multiple exit .txt files (e.g. section files) and merge into one ExitCodebook."""
    if not paths:
        raise ValueError("Need at least one path")
    merged_vars: List[ExitVariable] = []
    merged_sections: Dict[str, ExitSection] = {}
    seen_vars: set = set()
    for p in paths:
        cb = parse_exit_txt_codebook(p, source=source, year=year)
        for v in cb.variables:
            if v.name not in seen_vars:
                seen_vars.add(v.name)
                merged_vars.append(v)
        for s in cb.sections:
            if s.code not in merged_sections:
                merged_sections[s.code] = ExitSection(
                    code=s.code,
                    name=s.name,
                    level=s.level,
                    year=year,
                    variable_count=0,
                    variables=[],
                )
            for vname in s.variables:
                if vname not in merged_sections[s.code].variables:
                    merged_sections[s.code].variables.append(vname)
    for s in merged_sections.values():
        s.variable_count = len(s.variables)
    levels = {v.level for v in merged_vars}
    return ExitCodebook(
        source=source,
        year=year,
        release_type="Final Exit",
        sections=list(merged_sections.values()),
        variables=merged_vars,
        total_variables=len(merged_vars),
        total_sections=len(merged_sections),
        levels=levels,
        metadata={"file_paths": [str(p) for p in paths]},
        parsed_at=datetime.now(),
    )
