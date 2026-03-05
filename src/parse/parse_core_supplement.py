from pathlib import Path
import re
import traceback

from typing import List, Optional, Dict, Tuple

from datetime import datetime


from src.parse.save_codebook import save_core_supplement_codebook_json

from src.parse.parse_txt_codebook import parse_txt_codebook
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


def parse_txt_core_supplement(txt_core_supplement, year: int = None):
    """
    Parses the txt_core_supplement field from the input data.

    Args:
        txt_core_supplement (str): The txt_core_supplement field from the input data.
        year (str): The year associated with the codebook.

    Returns:
        str: The parsed txt_core_supplement codebook.
    """
    # Format appeared identical to the core codebook
    codebook = parse_txt_codebook(txt_core_supplement, source="hrs_core_supplement_codebook", year=year)
    return codebook

def _extract_year_from_filename(path: Path) -> int:
    """Extract year from filename (e.g., h2020cb.txt -> 2020)."""
    parts = path.parts
    for part in parts:
        year_match = re.search(r"(\d{4})", part)
        if year_match:
            return int(year_match.group(1))
    raise ValueError(f"Could not extract year from path: {path}")

def main() -> None:
    from src.parse.parse_codebooks import find_core_supplement_codebook_files
    """CLI: parse core imputation codebooks and save to JSON."""
    import argparse
    import sys

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
        default="hrs_core_supplement_codebook",
        help="Source name for codebooks (default: 'hrs_core_supplement_codebook')",
    )
    
    args = parser.parse_args()

    print(f"Finding supplement codebooks in {args.data_dir}...")

    # Covering all supplement for now
    
    files = find_core_supplement_codebook_files(args.data_dir, args.year, source=args.source)
    

    if not files:
        print("No supplement codebook files found.")
        sys.exit(1)


    # Group by year for merge  (year from filename or from path)
    files_by_year: Dict[int, List[Path]] = {}
    for p in files:
        y = _extract_year_from_filename(p)
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
                for p in paths:
                    print(f"Parsing {p}")
                    codebook = parse_txt_core_supplement(p, year=y)
                    out = save_core_supplement_codebook_json(codebook, args.output_dir, pretty=True)
                    print(f"Saved {codebook.total_variables} variables, {codebook.total_sections} sections -> {out}")
            else:
                print(f"No codebook file found for year {y}")
                continue
        except Exception as e:
            print(f" ERROR: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)
    print("Done.")


if __name__ == "__main__":
    main()