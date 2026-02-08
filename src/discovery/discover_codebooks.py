"""Discover and categorize variables from parsed codebooks according to their models."""

import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from collections import defaultdict, Counter
from dataclasses import dataclass, field

from ..models.cores import (
    Variable, VariableLevel, VariableType, Codebook,
    extract_base_name, get_year_prefix, HRS_YEARS, HRS_SECTION_CODES
)


@dataclass
class VariableCategory:
    """Represents a category of variables."""
    name: str
    description: str
    variable_names: List[str] = field(default_factory=list)
    count: int = 0
    years: Set[int] = field(default_factory=set)
    sections: Set[str] = field(default_factory=set)
    levels: Set[str] = field(default_factory=set)


@dataclass
class VariableCategorization:
    """Complete categorization of variables across all codebooks."""
    by_section: Dict[str, VariableCategory] = field(default_factory=dict)
    by_level: Dict[str, VariableCategory] = field(default_factory=dict)
    by_type: Dict[str, VariableCategory] = field(default_factory=dict)
    by_base_name: Dict[str, VariableCategory] = field(default_factory=dict)
    identifiers: VariableCategory = field(default_factory=lambda: VariableCategory(
        name="identifiers",
        description="Variables that serve as identifiers (HHID, PN, etc.)"
    ))
    derived: VariableCategory = field(default_factory=lambda: VariableCategory(
        name="derived",
        description="Derived/calculated variables"
    ))
    with_value_codes: VariableCategory = field(default_factory=lambda: VariableCategory(
        name="with_value_codes",
        description="Variables with discrete value codes"
    ))
    without_value_codes: VariableCategory = field(default_factory=lambda: VariableCategory(
        name="without_value_codes",
        description="Variables without discrete value codes"
    ))
    year_prefixed: VariableCategory = field(default_factory=lambda: VariableCategory(
        name="year_prefixed",
        description="Variables with year-specific prefixes (R, Q, P, etc.)"
    ))
    no_prefix: VariableCategory = field(default_factory=lambda: VariableCategory(
        name="no_prefix",
        description="Variables without year prefixes"
    ))
    total_variables: int = 0
    total_years: int = 0
    years_covered: Set[int] = field(default_factory=set)


def load_codebook_json(codebook_path: Path) -> Optional[Dict[str, Any]]:
    """Load a codebook JSON file."""
    try:
        with open(codebook_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {codebook_path}: {e}")
        return None


def find_parsed_codebooks(parsed_dir: Path, source: str = "hrs_core_codebook") -> List[Path]:
    """Find all parsed codebook JSON files."""
    codebooks = []
    source_dir = parsed_dir / source
    
    if not source_dir.exists():
        return codebooks
    
    for year_dir in source_dir.iterdir():
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        
        codebook_file = year_dir / f"codebook_{year_dir.name}.json"
        if codebook_file.exists():
            codebooks.append(codebook_file)
    
    return sorted(codebooks)


def categorize_variable(var_data: Dict[str, Any], year: int, categorization: VariableCategorization):
    """Categorize a single variable according to all model attributes."""
    var_name = var_data.get("name", "")
    section = var_data.get("section", "")
    level = var_data.get("level", "")
    var_type = var_data.get("type", "")
    has_value_codes = var_data.get("has_value_codes", False)
    is_identifier = var_data.get("is_identifier", False)
    is_derived = var_data.get("is_derived", False)
    
    # Categorize by section
    if section:
        if section not in categorization.by_section:
            categorization.by_section[section] = VariableCategory(
                name=f"section_{section}",
                description=f"Variables in section {section}"
            )
        cat = categorization.by_section[section]
        cat.variable_names.append(var_name)
        cat.count += 1
        cat.years.add(year)
        cat.sections.add(section)
        cat.levels.add(level)
    
    # Categorize by level
    if level:
        if level not in categorization.by_level:
            categorization.by_level[level] = VariableCategory(
                name=f"level_{level}",
                description=f"Variables at {level} level"
            )
        cat = categorization.by_level[level]
        cat.variable_names.append(var_name)
        cat.count += 1
        cat.years.add(year)
        cat.sections.add(section)
        cat.levels.add(level)
    
    # Categorize by type
    if var_type:
        if var_type not in categorization.by_type:
            categorization.by_type[var_type] = VariableCategory(
                name=f"type_{var_type}",
                description=f"{var_type} type variables"
            )
        cat = categorization.by_type[var_type]
        cat.variable_names.append(var_name)
        cat.count += 1
        cat.years.add(year)
        cat.sections.add(section)
        cat.levels.add(level)
    
    # Categorize by base name
    base_name = extract_base_name(var_name)
    if base_name not in categorization.by_base_name:
        categorization.by_base_name[base_name] = VariableCategory(
            name=f"base_{base_name}",
            description=f"Variables with base name {base_name}"
        )
    cat = categorization.by_base_name[base_name]
    cat.variable_names.append(var_name)
    cat.count += 1
    cat.years.add(year)
    cat.sections.add(section)
    cat.levels.add(level)
    
    # Categorize identifiers
    if is_identifier:
        categorization.identifiers.variable_names.append(var_name)
        categorization.identifiers.count += 1
        categorization.identifiers.years.add(year)
        categorization.identifiers.sections.add(section)
        categorization.identifiers.levels.add(level)
    
    # Categorize derived variables
    if is_derived:
        categorization.derived.variable_names.append(var_name)
        categorization.derived.count += 1
        categorization.derived.years.add(year)
        categorization.derived.sections.add(section)
        categorization.derived.levels.add(level)
    
    # Categorize by value codes
    if has_value_codes:
        categorization.with_value_codes.variable_names.append(var_name)
        categorization.with_value_codes.count += 1
        categorization.with_value_codes.years.add(year)
        categorization.with_value_codes.sections.add(section)
        categorization.with_value_codes.levels.add(level)
    else:
        categorization.without_value_codes.variable_names.append(var_name)
        categorization.without_value_codes.count += 1
        categorization.without_value_codes.years.add(year)
        categorization.without_value_codes.sections.add(section)
        categorization.without_value_codes.levels.add(level)
    
    # Categorize by prefix
    prefix = get_year_prefix(year)
    if prefix and var_name.startswith(prefix):
        categorization.year_prefixed.variable_names.append(var_name)
        categorization.year_prefixed.count += 1
        categorization.year_prefixed.years.add(year)
        categorization.year_prefixed.sections.add(section)
        categorization.year_prefixed.levels.add(level)
    else:
        categorization.no_prefix.variable_names.append(var_name)
        categorization.no_prefix.count += 1
        categorization.no_prefix.years.add(year)
        categorization.no_prefix.sections.add(section)
        categorization.no_prefix.levels.add(level)


def build_categorization_from_codebooks(
    codebooks: List[Dict[str, Any]],
) -> VariableCategorization:
    """Build variable categorization from in-memory codebook dicts (e.g. from MongoDB).

    Args:
        codebooks: List of codebook documents, each with 'year' and 'variables' (list of var dicts).

    Returns:
        VariableCategorization with by_section, by_level, by_type, special categories, etc.
    """
    categorization = VariableCategorization()
    for codebook_data in codebooks:
        year = codebook_data.get("year")
        if year is None:
            continue
        categorization.years_covered.add(year)
        categorization.total_years = len(categorization.years_covered)
        variables = codebook_data.get("variables", [])
        for var_data in variables:
            categorize_variable(var_data, year, categorization)
            categorization.total_variables += 1
    return categorization


def discover_codebooks(
    parsed_dir: Optional[Path] = None,
    source: str = "hrs_core_codebook",
    year: Optional[int] = None
) -> VariableCategorization:
    """Discover and categorize variables from parsed codebooks.
    
    Args:
        parsed_dir: Directory containing parsed codebook JSON files
        source: Source identifier (e.g., 'hrs_core_codebook')
        year: Optional year filter (if None, processes all years)
    
    Returns:
        VariableCategorization object with all categorizations
    """
    if parsed_dir is None:
        parsed_dir = Path(__file__).parent.parent.parent / "data" / "parsed"
    
    # Find codebook files
    codebook_files = find_parsed_codebooks(parsed_dir, source)
    
    if year:
        codebook_files = [f for f in codebook_files if f.parent.name == str(year)]
    
    if not codebook_files:
        print(f"No codebook files found in {parsed_dir / source}")
        return VariableCategorization()
    
    print(f"Found {len(codebook_files)} codebook file(s)")
    
    # Initialize categorization
    categorization = VariableCategorization()
    
    # Process each codebook
    for codebook_file in codebook_files:
        codebook_data = load_codebook_json(codebook_file)
        if not codebook_data:
            continue
        
        year = codebook_data.get("year")
        if not year:
            # Try to extract from filename
            try:
                year = int(codebook_file.parent.name)
            except ValueError:
                continue
        
        categorization.years_covered.add(year)
        categorization.total_years = len(categorization.years_covered)
        
        variables = codebook_data.get("variables", [])
        print(f"Processing {year}: {len(variables)} variables")
        
        for var_data in variables:
            categorize_variable(var_data, year, categorization)
            categorization.total_variables += 1
    
    return categorization


def print_categorization_summary(categorization: VariableCategorization):
    """Print a summary of variable categorization."""
    print("\n" + "=" * 80)
    print("VARIABLE CATEGORIZATION SUMMARY")
    print("=" * 80)
    
    print(f"\nTotal Variables: {categorization.total_variables:,}")
    print(f"Years Covered: {categorization.total_years} ({sorted(categorization.years_covered)})")
    
    # By Section
    print(f"\n--- By Section ({len(categorization.by_section)} sections) ---")
    for section_code in sorted(categorization.by_section.keys()):
        cat = categorization.by_section[section_code]
        print(f"  {section_code:4s}: {cat.count:6,} variables ({len(cat.years)} years)")
    
    # By Level
    print(f"\n--- By Level ({len(categorization.by_level)} levels) ---")
    for level in sorted(categorization.by_level.keys()):
        cat = categorization.by_level[level]
        print(f"  {level:20s}: {cat.count:6,} variables ({len(cat.years)} years)")
    
    # By Type
    print(f"\n--- By Type ({len(categorization.by_type)} types) ---")
    for var_type in sorted(categorization.by_type.keys()):
        cat = categorization.by_type[var_type]
        print(f"  {var_type:15s}: {cat.count:6,} variables ({len(cat.years)} years)")
    
    # Special Categories
    print(f"\n--- Special Categories ---")
    print(f"  Identifiers:        {categorization.identifiers.count:6,} variables")
    print(f"  Derived:            {categorization.derived.count:6,} variables")
    print(f"  With Value Codes:   {categorization.with_value_codes.count:6,} variables")
    print(f"  Without Value Codes: {categorization.without_value_codes.count:6,} variables")
    print(f"  Year Prefixed:     {categorization.year_prefixed.count:6,} variables")
    print(f"  No Prefix:         {categorization.no_prefix.count:6,} variables")
    
    # Base Names (top 20)
    print(f"\n--- Top 20 Base Names (by count) ---")
    base_name_counts = [(name, cat.count) for name, cat in categorization.by_base_name.items()]
    base_name_counts.sort(key=lambda x: x[1], reverse=True)
    for base_name, count in base_name_counts[:20]:
        cat = categorization.by_base_name[base_name]
        print(f"  {base_name:20s}: {count:6,} variables ({len(cat.years)} years, {len(cat.sections)} sections)")


def save_categorization(
    categorization: VariableCategorization,
    output_path: Path,
    include_variable_names: bool = False
):
    """Save categorization to JSON file."""
    output_data = {
        "summary": {
            "total_variables": categorization.total_variables,
            "total_years": categorization.total_years,
            "years_covered": sorted(list(categorization.years_covered))
        },
        "by_section": {
            section: {
                "count": cat.count,
                "years": sorted(list(cat.years)),
                "sections": sorted(list(cat.sections)),
                "levels": sorted(list(cat.levels)),
                "variable_names": cat.variable_names if include_variable_names else []
            }
            for section, cat in categorization.by_section.items()
        },
        "by_level": {
            level: {
                "count": cat.count,
                "years": sorted(list(cat.years)),
                "sections": sorted(list(cat.sections)),
                "levels": sorted(list(cat.levels)),
                "variable_names": cat.variable_names if include_variable_names else []
            }
            for level, cat in categorization.by_level.items()
        },
        "by_type": {
            var_type: {
                "count": cat.count,
                "years": sorted(list(cat.years)),
                "sections": sorted(list(cat.sections)),
                "levels": sorted(list(cat.levels)),
                "variable_names": cat.variable_names if include_variable_names else []
            }
            for var_type, cat in categorization.by_type.items()
        },
        "special_categories": {
            "identifiers": {
                "count": categorization.identifiers.count,
                "years": sorted(list(categorization.identifiers.years)),
                "variable_names": categorization.identifiers.variable_names if include_variable_names else []
            },
            "derived": {
                "count": categorization.derived.count,
                "years": sorted(list(categorization.derived.years)),
                "variable_names": categorization.derived.variable_names if include_variable_names else []
            },
            "with_value_codes": {
                "count": categorization.with_value_codes.count,
                "years": sorted(list(categorization.with_value_codes.years)),
                "variable_names": categorization.with_value_codes.variable_names if include_variable_names else []
            },
            "without_value_codes": {
                "count": categorization.without_value_codes.count,
                "years": sorted(list(categorization.without_value_codes.years)),
                "variable_names": categorization.without_value_codes.variable_names if include_variable_names else []
            },
            "year_prefixed": {
                "count": categorization.year_prefixed.count,
                "years": sorted(list(categorization.year_prefixed.years)),
                "variable_names": categorization.year_prefixed.variable_names if include_variable_names else []
            },
            "no_prefix": {
                "count": categorization.no_prefix.count,
                "years": sorted(list(categorization.no_prefix.years)),
                "variable_names": categorization.no_prefix.variable_names if include_variable_names else []
            }
        },
        "base_names_summary": {
            base_name: {
                "count": cat.count,
                "years": sorted(list(cat.years)),
                "sections": sorted(list(cat.sections)),
                "sample_variables": cat.variable_names[:10] if cat.variable_names else []
            }
            for base_name, cat in sorted(
                categorization.by_base_name.items(),
                key=lambda x: x[1].count,
                reverse=True
            )[:100]  # Top 100 base names
        }
    }
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\nCategorization saved to: {output_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Discover and categorize variables from parsed codebooks"
    )
    parser.add_argument(
        "--parsed-dir",
        type=Path,
        default=Path(__file__).parent.parent.parent / "data" / "parsed",
        help="Directory containing parsed codebook JSON files"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="hrs_core_codebook",
        help="Source identifier (e.g., 'hrs_core_codebook')"
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Process only a specific year"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON file path for categorization results"
    )
    parser.add_argument(
        "--include-names",
        action="store_true",
        help="Include variable names in output (makes file larger)"
    )
    
    args = parser.parse_args()
    
    # Discover and categorize
    categorization = discover_codebooks(
        parsed_dir=args.parsed_dir,
        source=args.source,
        year=args.year
    )
    
    # Print summary
    print_categorization_summary(categorization)
    
    # Save if output path provided
    if args.output:
        save_categorization(
            categorization,
            args.output,
            include_variable_names=args.include_names
        )
