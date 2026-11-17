"""Generate tests/fixtures/planner_fixtures.json: the Python side of the Python <-> JavaScript consistency tests.

    python tests/make_fixtures.py

The JavaScript planner (dashboard/src/js/planner-core.js) must give the same Hijri dates and the same state-salary
paydays as the Python analysis (hijridate + bayyin.paydays). This file holds the Python answers; the Node test checks them.
It also holds the dashboard inputs the planner reads, so the JS test does not need to parse CSV.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd
from hijridate import Gregorian

from bayyin.paydays import build_payday_calendar

ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_DATA = ROOT / "data_clean" / "dashboard_data"
OUTPUT = Path(__file__).resolve().parent / "fixtures" / "planner_fixtures.json"


def _rows(name: str) -> list[dict]:
    return list(csv.DictReader(open(DASHBOARD_DATA / f"{name}.csv", encoding="utf-8")))


def build() -> dict:
    days = pd.date_range("2026-01-01", "2028-12-31", freq="D")
    hijri = [[d.strftime("%Y-%m-%d"), h.year, h.month, h.day]
             for d, h in ((d, Gregorian(d.year, d.month, d.day).to_hijri()) for d in days)]
    calendar = build_payday_calendar("2026-01-01", "2028-12-01")
    salary = calendar[calendar["Program"] == "salary_27"]["Pay_Date"].dt.strftime("%Y-%m-%d").tolist()
    model = [{"key": r["key"], "c": float(r["change_pct"]), "conclusion": r["conclusion"]} for r in _rows("model_results")]
    hourly = [{"h": int(r["hour"]), "rd": float(r["ramadan_per_day"]), "os": float(r["other_share"])} for r in _rows("hourly")]
    weekday_hours = [{"wd": r["weekday"], "h": int(r["hour"]), "donations": int(r["donations"])} for r in _rows("weekday_hour")]
    return {"hijri": hijri, "salary_paydays": salary, "model": model, "hourly": hourly, "weekday_hours": weekday_hours}


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
