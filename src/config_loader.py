"""Load source configuration from config/sources.yaml."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Project root: assume this file is in src/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SOURCES_PATH = _PROJECT_ROOT / "config" / "sources.yaml"

_SOURCES_CACHE: Optional[List[Dict[str, Any]]] = None


def load_sources_config(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load sources list from config/sources.yaml."""
    global _SOURCES_CACHE
    if _SOURCES_CACHE is not None:
        return _SOURCES_CACHE
    p = path or _SOURCES_PATH
    if not p.exists():
        _SOURCES_CACHE = []
        return _SOURCES_CACHE
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _SOURCES_CACHE = data.get("sources") or []
    return _SOURCES_CACHE


def get_source_by_name(name: str, path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Return the source config dict for the given name, or None."""
    for s in load_sources_config(path):
        if s.get("name") == name:
            return s
    return None


def get_years_for_source(name: str, path: Optional[Path] = None) -> List[int]:
    """Return the list of configured years for a source (e.g. hrs_exit_codebook)."""
    source = get_source_by_name(name, path)
    if not source:
        return []
    years = source.get("years")
    if isinstance(years, list):
        return [int(y) for y in years if isinstance(y, (int, str)) and str(y).isdigit()]
    return []


def get_patterns_for_source(name: str, path: Optional[Path] = None) -> List[str]:
    """Return URL patterns for a source (from patterns[pattern_group])."""
    with open(path or _SOURCES_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    patterns_map = data.get("patterns") or {}
    source = get_source_by_name(name, path)
    if not source:
        return []
    group = source.get("pattern_group")
    if not group or group not in patterns_map:
        return []
    return list(patterns_map[group]) if isinstance(patterns_map[group], list) else []
