"""Build the dashboard: dashboard/src/ + the aggregated tables  ->  one self-contained index.html.

    python dashboard/build.py              # prepare the tables, then build index.html
    python dashboard/build.py --no-data    # only rebuild index.html from the tables already in data_clean/dashboard_data
    python dashboard/build.py --check      # fail if index.html is out of date (nothing is written)

The page stays a single file (data inlined) so it can be opened from disk and published on GitHub Pages as is.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

if __package__ in (None, ""):  # run as a script: make `dashboard` importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard import prepare_data

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "dashboard" / "src"
DATA_DIR = REPO_ROOT / "data_clean" / "dashboard_data"
OUTPUT = REPO_ROOT / "index.html"

# Order matters: later files use what earlier ones define (they share one scope).
CSS_FILES = ["base.css", "hero-nav.css", "sections.css", "planner.css"]
JS_FILES = ["util.js", "data.js", "sections.js", "charts.js", "planner.js", "main.js"]
DATA_TABLES = ["summary", "weekday_hour", "hourly", "weekday", "daily", "hijri_month", "day_of_month", "ramadan_days",
               "top_projects", "model_results"]
PLACEHOLDERS = ["{{STYLES}}", "{{DATA}}", "{{PLANNER_CORE}}", "{{APP_JS}}"]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_data(data_dir: Path = DATA_DIR) -> dict[str, list[dict]]:
    """The aggregated CSV tables as lists of rows (strings, converted by the page)."""
    return {name: list(csv.DictReader(open(data_dir / f"{name}.csv", encoding="utf-8"))) for name in DATA_TABLES}


def render(src: Path = SRC, data_dir: Path = DATA_DIR) -> str:
    """Assemble index.html from the source files and the data tables."""
    parts = {
        "{{STYLES}}": "".join(_read(src / "css" / name) for name in CSS_FILES),
        "{{DATA}}": json.dumps(load_data(data_dir), ensure_ascii=False, separators=(",", ":")),
        "{{PLANNER_CORE}}": _read(src / "js" / "planner-core.js"),
        "{{APP_JS}}": "".join(_read(src / "js" / name) for name in JS_FILES),
    }
    html = _read(src / "index.html")
    for placeholder in PLACEHOLDERS:
        assert html.count(placeholder) == 1, f"{placeholder} must appear exactly once in index.html"
    for placeholder, content in parts.items():
        html = html.replace(placeholder, content.rstrip("\n") + ("\n" if placeholder in ("{{STYLES}}",) else ""))
    return html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--no-data", action="store_true", help="do not regenerate the aggregated tables")
    parser.add_argument("--check", action="store_true", help="exit with an error if index.html is out of date")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    if not args.no_data and not args.check:
        prepare_data.prepare(out_dir=DATA_DIR)
    html = render()
    if args.check:
        current = _read(args.output) if args.output.exists() else ""
        if current != html:
            print(f"{args.output} is out of date: run  python dashboard/build.py", file=sys.stderr)
            return 1
        print(f"{args.output} is up to date")
        return 0
    args.output.write_text(html, encoding="utf-8")
    print(f"Wrote {args.output} ({len(html.encode('utf-8')) / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
