from src.parse.parse_core_imputations_codebooks import parse_core_imputations_txt_codebook
from src.parse.parse_exit_codebook import _extract_year_from_path
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import traceback

def main() -> None:
    """CLI: parse exit imputation codebooks and save to JSON."""
    import argparse
    import sys

    from src.parse.parse_codebooks import find_imputations_codebook_files
    from .save_codebook import save_core_imputations_codebook_json

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
        default="hrs_exit_imputations_codebook",
        help="Source identifier",
    )
    args = parser.parse_args()

    print(f"Finding exit imputation codebooks in {args.data_dir}...")

    files = find_imputations_codebook_files(args.data_dir, args.year, type="Exit")
    if not files:
        print("No exit imputation codebook files found.")
        sys.exit(1)

    # Group by year for merge  (year from filename or from path)
    files_by_year: Dict[int, List[Path]] = {}
    for p in files:
        y = _extract_year_from_path(p)
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
                print(f"Parsing {paths[0]}")
                codebook = parse_core_imputations_txt_codebook(paths[0], source=args.source, year=y)
            else:
                print(f"No codebook file found for year {y}")
                continue
            out = save_core_imputations_codebook_json(codebook, args.output_dir, pretty=True)
            print(f"Saved {codebook.total_variables} variables, {codebook.total_sections} sections -> {out}")
        except Exception as e:
            print(f" ERROR: {e}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)
    print("Done.")


if __name__ == "__main__":
    main()