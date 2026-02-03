"""Save parsed codebooks to structured JSON files."""

import json
from pathlib import Path
from typing import Optional
from datetime import datetime

from src.models.cores import Codebook, CrossYearVariableCatalog, VariableTemporalMapping


def save_codebook_json(
    codebook: Codebook,
    output_dir: Path,
    pretty: bool = True,
) -> Path:
    """Save a codebook to a structured JSON file.
    
    Args:
        codebook: Parsed Codebook object
        output_dir: Base output directory
        pretty: Whether to format JSON with indentation
    
    Returns:
        Path to the saved JSON file
    """
    # Create directory structure: output_dir/source/year/
    output_path = output_dir / codebook.source / str(codebook.year)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Save main codebook file
    codebook_file = output_path / f"codebook_{codebook.year}.json"
    with open(codebook_file, "w", encoding="utf-8") as f:
        json.dump(
            codebook.model_dump(mode="json"),
            f,
            indent=2 if pretty else None,
            ensure_ascii=False,
            default=str,  # Handle datetime and enum serialization
        )
    
    # Save variables by section
    sections_dir = output_path / "sections"
    sections_dir.mkdir(exist_ok=True)
    
    for section in codebook.sections:
        section_vars = [v for v in codebook.variables if v.section == section.code]
        section_data = {
            "section": section.model_dump(mode="json"),
            "variables": [v.model_dump(mode="json") for v in section_vars],
        }
        
        section_file = sections_dir / f"section_{section.code}.json"
        with open(section_file, "w", encoding="utf-8") as f:
            json.dump(
                section_data,
                f,
                indent=2 if pretty else None,
                ensure_ascii=False,
                default=str,
            )
    
    # Save variables index (quick lookup)
    variables_index = {
        "year": codebook.year,
        "source": codebook.source,
        "total_variables": codebook.total_variables,
        "variables": [
            {
                "name": v.name,
                "section": v.section,
                "level": v.level.value,
                "description": v.description,
                "type": v.type.value,
            }
            for v in codebook.variables
        ],
    }
    
    index_file = output_path / "variables_index.json"
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(
            variables_index,
            f,
            indent=2 if pretty else None,
            ensure_ascii=False,
        )
    
    return codebook_file


def save_cross_year_catalog(
    catalog: CrossYearVariableCatalog,
    output_dir: Path,
    pretty: bool = True,
) -> Path:
    """Save cross-year variable catalog to JSON.
    
    Args:
        catalog: CrossYearVariableCatalog object
        output_dir: Base output directory
        pretty: Whether to format JSON with indentation
    
    Returns:
        Path to the saved JSON file
    """
    output_path = output_dir / "catalog"
    output_path.mkdir(parents=True, exist_ok=True)
    
    catalog_file = output_path / "cross_year_catalog.json"
    
    # Convert to dict, handling nested models
    catalog_dict = {
        "years": sorted(list(catalog.years)),
        "base_variables": {
            name: mapping.model_dump(mode="json")
            for name, mapping in catalog.base_variables.items()
        },
        "year_codebooks": {
            str(year): {
                "source": cb.source,
                "year": cb.year,
                "total_variables": cb.total_variables,
                "total_sections": cb.total_sections,
            }
            for year, cb in catalog.year_codebooks.items()
        },
    }
    
    with open(catalog_file, "w", encoding="utf-8") as f:
        json.dump(
            catalog_dict,
            f,
            indent=2 if pretty else None,
            ensure_ascii=False,
            default=str,
        )
    
    return catalog_file
