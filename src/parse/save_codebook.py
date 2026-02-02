"""JSON save utilities for parsed codebooks and cross-year catalog."""

import json
from pathlib import Path
from typing import Any

from .models import Codebook, CrossYearVariableCatalog


def _to_json_safe(obj: Any) -> Any:
    """Convert object to JSON-serializable form (sets -> lists, etc.)."""
    if isinstance(obj, set):
        return sorted(obj) if all(isinstance(x, (int, str)) for x in obj) else list(obj)
    if isinstance(obj, dict):
        return {str(k): _to_json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_json_safe(item) for item in obj]
    return obj


def save_codebook_json(codebook: Codebook, output_dir: Path) -> Path:
    """Save a parsed codebook to a JSON file.

    Args:
        codebook: Parsed Codebook instance.
        output_dir: Directory to write the JSON file.

    Returns:
        Path to the written file (e.g. output_dir/codebook_hrs_core_codebook_2020.json).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"codebook_{codebook.source}_{codebook.year}.json"
    out_path = output_dir / filename

    data = codebook.model_dump(mode="json")
    data = _to_json_safe(data)

    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return out_path


def save_cross_year_catalog(catalog: CrossYearVariableCatalog, output_dir: Path) -> Path:
    """Save the cross-year variable catalog to a JSON file.

    Args:
        catalog: CrossYearVariableCatalog instance.
        output_dir: Directory to write the JSON file.

    Returns:
        Path to the written file (e.g. output_dir/cross_year_catalog.json).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / "cross_year_catalog.json"

    data = catalog.model_dump(mode="json")
    data = _to_json_safe(data)

    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return out_path
