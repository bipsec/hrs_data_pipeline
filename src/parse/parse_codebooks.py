"""Main script for parsing HRS codebook files and saving to structured JSON."""

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from src.config_loader import get_years_for_source

from .parse_txt_codebook import parse_txt_codebook
from .parse_early_1992_1994 import parse_and_merge_early_codebook
from .parse_exit_codebook import parse_exit_codebook, parse_and_merge_exit_codebook
from .save_codebook import save_codebook_json, save_exit_codebook_json
from src.models.cores import (
    CrossYearVariableCatalog,
    VariableTemporalMapping,
    extract_base_name,
    get_year_prefix,
    YEAR_PREFIX_MAP,
    HRS_YEARS,
)


# 1992/1994: exclude toc and master-code-only files (no variable blocks)
_EARLY_EXCLUDE_BASENAMES = frozenset({"01_COVER.TXT", "01_COVER.txt", "02_MCODE.TXT", "02_MCODE.txt", "01_W2MAS.TXT", "01_W2MAS.txt"})


def find_codebook_files(data_dir: Path, year: Optional[int] = None) -> List[Path]:
    """Find codebook files in the data directory.
    
    - 1992: HRS Data/1992/Core/h92core/h92cb/*.TXT (multiple section files)
    - 1994: HRS Data/1994/Core/h94core/h94cb/*.TXT (multiple section files)
    - 1996+: HRS Data/{year}/Core/h{yy}cb/h{year}cb.txt or h{yy}cb.txt (single file)
    """
    codebooks: List[Path] = []
    
    if year:
        year_dirs = [data_dir / "HRS Data" / str(year)]
    else:
        hrs_data_dir = data_dir / "HRS Data"
        if not hrs_data_dir.exists():
            return []
        year_dirs = [d for d in hrs_data_dir.iterdir() if d.is_dir() and d.name.isdigit()]
    
    for year_dir in year_dirs:
        if not year_dir.exists():
            continue
        core_dir = year_dir / "Core"
        if not core_dir.exists():
            continue
        
        year_int = int(year_dir.name)
        year_2d = year_int % 100
        
        # 1992, 1994: multi-file layout h92core/h92cb/*.TXT or h94core/h94cb/*.TXT
        if year_int in (1992, 1994):
            early_core = core_dir / f"h{year_2d}core" / f"h{year_2d}cb"
            if early_core.exists():
                for f in early_core.iterdir():
                    if f.is_file() and f.suffix.upper() == ".TXT" and f.name not in _EARLY_EXCLUDE_BASENAMES:
                        if f not in codebooks:
                            codebooks.append(f)
            continue
        
        # 1996+: single (or few) codebook file(s) under h*cb directory
        for subdir in core_dir.iterdir():
            if subdir.is_dir() and "cb" in subdir.name.lower():
                candidates = [
                    subdir / f"h{year_dir.name}cb.txt",
                    subdir / f"h{year_2d:02d}cb.txt",
                    subdir / f"{subdir.name}.txt",
                ]
                for codebook_file in candidates:
                    if codebook_file.exists() and codebook_file not in codebooks:
                        codebooks.append(codebook_file)
                        break
    
    return sorted(codebooks)


def find_exit_codebook_files(
    data_dir: Path,
    year: Optional[int] = None,
) -> List[Path]:
    """Find exit codebook files. Uses years from config/sources.yaml (hrs_exit_codebook).

    Looks under data_dir / 'HRS Data' / {year} / 'Exit' / x{yy}cb/ for:
    - Single combined file: x{year}cb.txt (e.g. x2022cb.txt) or x{yy}cb.txt (e.g. x96cb.txt)
    - Otherwise all *.txt in that directory.
    If no .txt there, looks for .htm/.html under Exit or raw/exit.
    data_dir is resolved to absolute so relative paths work when run from any cwd.
    """
    base = data_dir.resolve()
    years = get_years_for_source("hrs_exit_codebook")
    if year is not None:
        years = [y for y in years if y == year]
    codebooks: List[Path] = []
    for y in years:
        yy = y % 100
        exit_dir = base / "HRS Data" / str(y) / "Exit"
        # Prefer x{yy}cb (e.g. x95cb); also check x{year}cb (e.g. x1995cb) for 4-digit naming
        xcb_dir = exit_dir / f"x{yy:02d}cb"
        xcb_dir_4 = exit_dir / f"x{y}cb"
        found: List[Path] = []
        for cand_dir in (xcb_dir, xcb_dir_4):
            if not cand_dir.exists():
                continue
            combined_4 = cand_dir / f"x{y}cb.txt"
            combined_2 = cand_dir / f"x{yy:02d}cb.txt"
            if combined_4.exists():
                found = [combined_4]
                break
            if combined_2.exists():
                found = [combined_2]
                break
            txts = sorted(f for f in cand_dir.glob("*.txt") if f.is_file())
            if txts:
                found = txts
                break
        if found:
            codebooks.extend(found)
        else:
            for fallback in (exit_dir, base / "raw" / "exit" / str(y), base / "Exit" / str(y)):
                if not fallback.exists():
                    continue
                for f in fallback.rglob("*"):
                    if f.is_file() and f.suffix.lower() in (".htm", ".html"):
                        codebooks.append(f)
    return sorted(set(codebooks))


def _year_from_path(path: Path) -> Optional[int]:
    """Extract year from path like .../HRS Data/1992/Core/... or .../1994/..."""
    parts = path.parts
    for i, p in enumerate(parts):
        if p.isdigit() and len(p) == 4 and 1990 <= int(p) <= 2030:
            return int(p)
    return None


def group_codebook_files_by_year(
    codebook_files: List[Path],
) -> List[Tuple[int, List[Path]]]:
    """Group codebook file paths by year. For 1992/1994 multiple files per year."""
    by_year: dict = {}
    for p in codebook_files:
        y = _year_from_path(p)
        if y is None:
            y = int(p.parent.parent.parent.name) if p.parent.parent.parent.name.isdigit() else None
        if y is not None:
            by_year.setdefault(y, []).append(p)
    return sorted((year, sorted(paths)) for year, paths in by_year.items())


def build_cross_year_catalog(codebooks: List[dict]) -> CrossYearVariableCatalog:
    """Build cross-year variable catalog from parsed codebooks (1992-2022)."""
    catalog = CrossYearVariableCatalog()
    
    # Add codebooks
    for cb_data in codebooks:
        codebook = cb_data["codebook"]
        year = codebook.year
        catalog.year_codebooks[year] = codebook
        catalog.years.add(year)
        
        # Build temporal mappings
        for var in codebook.variables:
            # Extract base name (remove year prefix like R, Q, P, E, etc.)
            base_name = extract_base_name(var.name)
            
            if base_name not in catalog.base_variables:
                catalog.base_variables[base_name] = VariableTemporalMapping(
                    base_name=base_name,
                    years=set(),
                )
            
            mapping = catalog.base_variables[base_name]
            mapping.years.add(year)
            
            # Extract prefix using the year prefix map
            prefix = get_year_prefix(year)
            if prefix and var.name.startswith(prefix):
                mapping.year_prefixes[year] = prefix
            elif var.name != base_name:
                # Fallback: extract prefix manually
                prefix = var.name[: len(var.name) - len(base_name)] if var.name != base_name else ""
                if prefix:
                    mapping.year_prefixes[year] = prefix
            
            # Update first/last year
            if mapping.first_year is None or year < mapping.first_year:
                mapping.first_year = year
            if mapping.last_year is None or year > mapping.last_year:
                mapping.last_year = year
    
    # Calculate year gaps for each variable
    for mapping in catalog.base_variables.values():
        if len(mapping.years) > 1:
            sorted_years = sorted(mapping.years)
            gaps = []
            for i in range(len(sorted_years) - 1):
                if sorted_years[i + 1] - sorted_years[i] > 2:  # More than 2 years apart (biennial)
                    gaps.append((sorted_years[i] + 2, sorted_years[i + 1] - 2))
            mapping.year_gaps = gaps
    
    return catalog


def main():
    """Main entry point for parsing codebooks."""
    parser = argparse.ArgumentParser(
        description="Parse HRS codebook files and save to structured JSON"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).parent.parent.parent / "data",
        help="Directory containing HRS Data folder",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).parent.parent.parent / "data" / "parsed",
        help="Output directory for parsed JSON files",
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Process only a specific year",
    )
    parser.add_argument(
        "--source",
        type=str,
        default="hrs_core_codebook",
        help="Source identifier (e.g. hrs_core_codebook, hrs_exit_codebook from config/sources.yaml)",
    )
    parser.add_argument(
        "--build-catalog",
        action="store_true",
        help="Build cross-year variable catalog (core only)",
    )
    
    args = parser.parse_args()
    
    # Exit codebook: use config years and find files under data/HRS Data/{year}/Exit/x{yy}cb/*.txt
    if args.source == "hrs_exit_codebook":
        print(f"Searching for exit codebook files in: {args.data_dir}")
        codebook_files = find_exit_codebook_files(args.data_dir, args.year)
        if not codebook_files:
            print("No exit codebook files found. Place .txt under data/HRS Data/{year}/Exit/x{yy}cb/ (e.g. x20cb/x2020cb.txt)")
            sys.exit(1)
        exit_by_year = {}
        for p in codebook_files:
            y = _year_from_path(p)
            if y is None and len(p.parts) >= 2 and p.parts[-2].isdigit():
                y = int(p.parts[-2])
            if y is not None:
                exit_by_year.setdefault(y, []).append(p)
        for year, paths in sorted(exit_by_year.items()):
            try:
                if len(paths) == 1:
                    print(f"\nParsing: {paths[0]}")
                    codebook = parse_exit_codebook(paths[0], source=args.source, year=year)
                else:
                    print(f"\nParsing {len(paths)} files for {year} (merge)")
                    codebook = parse_and_merge_exit_codebook(paths, year=year, source=args.source)
                out = save_exit_codebook_json(codebook, args.output_dir)
                print(f"  Parsed {codebook.total_variables} variables in {codebook.total_sections} sections; saved to {out}")
            except Exception as e:
                print(f"  ERROR: {e}")
                import traceback
                traceback.print_exc()
        print("\n[OK] Exit codebook parsing complete.")
        return
    
    # Core codebook
    print(f"Searching for codebook files in: {args.data_dir}")
    codebook_files = find_codebook_files(args.data_dir, args.year)
    
    if not codebook_files:
        print("No codebook files found!")
        sys.exit(1)
    
    year_groups = group_codebook_files_by_year(codebook_files)
    print(f"Found {sum(len(p) for _, p in year_groups)} file(s) across {len(year_groups)} year(s)")
    
    parsed_codebooks = []
    for year, paths in year_groups:
        try:
            if year in (1992, 1994) and len(paths) > 1:
                print(f"\nParsing {len(paths)} files for {year} (early format)...")
                codebook = parse_and_merge_early_codebook(paths, year=year, source=args.source)
                print(f"  Parsed {codebook.total_variables} variables in {codebook.total_sections} sections")
            else:
                codebook_file = paths[0]
                print(f"\nParsing: {codebook_file}")
                codebook = parse_txt_codebook(codebook_file, source=args.source, year=year)
                print(f"  Parsed {codebook.total_variables} variables in {codebook.total_sections} sections")
            
            output_file = save_codebook_json(codebook, args.output_dir)
            print(f"  Saved to: {output_file}")
            parsed_codebooks.append({"file": paths[0] if len(paths) == 1 else paths[0].parent, "codebook": codebook})
        except Exception as e:
            print(f"  ERROR: Failed to parse year {year}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    if args.build_catalog and parsed_codebooks:
        print("\nBuilding cross-year variable catalog...")
        catalog = build_cross_year_catalog(parsed_codebooks)
        catalog_file = save_cross_year_catalog(catalog, args.output_dir)
        print(f"  Saved catalog to: {catalog_file}")
        print(f"  Found {len(catalog.base_variables)} base variables across {len(catalog.years)} years")
    
    print(f"\n[OK] Parsing complete! Processed {len(parsed_codebooks)} codebook(s)")


if __name__ == "__main__":
    main()
