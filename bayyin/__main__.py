"""Run the whole analysis from the command line:  python -m bayyin  [--out DIR]"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no window: just save the figures

from . import pipeline
from .config import INPUT_CSV, OUT_DIR


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m bayyin", description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT_CSV, help="the cleaned CSV (default: data_clean/...)")
    parser.add_argument("--out", type=Path, default=OUT_DIR, help="where tables/ and figures/ are written")
    args = parser.parse_args()

    results = pipeline.run_all(args.input)
    table_dir = pipeline.save_tables(results.tables, args.out / "tables")
    pipeline.save_figures(results, args.out / "figures")
    print(f"Saved {len(results.tables)} tables to {table_dir}/ and 4 figures to {args.out / 'figures'}/")
    print(results.tables["candidate_periods"].to_string(index=False))


if __name__ == "__main__":
    main()
