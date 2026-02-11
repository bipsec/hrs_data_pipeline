"""Modular codebook parsing: dispatch by source name using config/sources.yaml."""

from pathlib import Path
from typing import List, Optional, Union

from src.config_loader import get_source_by_name, get_years_for_source, load_sources_config
from src.models.cores import Codebook
from src.models.exits import ExitCodebook

from .parse_exit_codebook import parse_exit_codebook
from .parse_post_exit_codebook import parse_post_exit_codebook
from .parse_txt_codebook import parse_txt_codebook


def parse_codebook_for_source(
    file_path: Path,
    source_name: str,
    year: Optional[int] = None,
) -> Union[Codebook, ExitCodebook]:
    """Parse a single codebook file using the parser for the given source.

    Source is looked up in config/sources.yaml. Supported sources:
    - hrs_exit_codebook: HTML exit codebook -> ExitCodebook
    - hrs_core_codebook: TXT core codebook -> Codebook (single file; for 1992/1994 use batch)

    Args:
        file_path: Path to the codebook file (HTML or TXT).
        source_name: Source identifier (e.g. 'hrs_exit_codebook', 'hrs_core_codebook').
        year: Optional year; inferred from path if not set.

    Returns:
        Parsed Codebook (core) or ExitCodebook (exit).

    Raises:
        ValueError: If source_name is not supported or not in config.
    """
    source = get_source_by_name(source_name)
    if not source:
        raise ValueError(
            f"Unknown source '{source_name}'. "
            "Check config/sources.yaml for names (e.g. hrs_exit_codebook, hrs_core_codebook)."
        )
    name = source.get("name", "")
    source_type = (source.get("type") or "").lower()
    pattern_group = (source.get("pattern_group") or "").lower()

    if name == "hrs_exit_codebook" or (
        source_type == "html" and "exit" in pattern_group and "post" not in pattern_group
    ):
        return parse_exit_codebook(file_path, source=name, year=year)

    if name == "hrs_post_exit_codebook" or (
        source_type == "html" and "post_exit" in pattern_group
    ):
        return parse_post_exit_codebook(file_path, source=name, year=year)

    if name == "hrs_core_codebook" or (
        source_type == "txt" or "core" in pattern_group
    ):
        return parse_txt_codebook(file_path, source=name, year=year)

    raise ValueError(
        f"No parser registered for source '{source_name}' (type={source_type}, pattern_group={pattern_group})."
    )


def get_parser_source_types() -> List[str]:
    """Return list of source names that have a registered parser (from config)."""
    supported = []
    for s in load_sources_config():
        name = s.get("name")
        if not name:
            continue
        if name in ("hrs_exit_codebook", "hrs_core_codebook", "hrs_post_exit_codebook"):
            supported.append(name)
    return supported


def exit_codebook_years() -> List[int]:
    """Return configured years for hrs_exit_codebook from config/sources.yaml."""
    return get_years_for_source("hrs_exit_codebook")
