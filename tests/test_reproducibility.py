"""The committed results can be reproduced exactly from the committed data (golden tests)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from bayyin import pipeline
from dashboard import build, prepare_data

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def results():
    return pipeline.run_all()


def test_analysis_reproduces_every_committed_table_byte_for_byte(results, tmp_path):
    pipeline.save_tables(results.tables, tmp_path)
    committed = sorted((ROOT / "outputs" / "tables").glob("*.csv"))
    assert len(committed) == len(results.tables) == 15
    different = [p.name for p in committed if (tmp_path / p.name).read_bytes() != p.read_bytes()]
    assert not different, f"tables that changed: {different}"


def test_the_headline_result_is_unchanged(results):
    top = results.tables["candidate_periods"]
    assert list(top["Factor"]) == ["Ramadan, last 10 days", "Ramadan, days 1-20", "Dhu al-Hijjah 1-9 (incl. Arafah)",
                                   "Friday (vs Sunday)", "State salaries (27th)"]
    assert list(top["Change_%"]) == [484.0, 155.6, 153.1, 53.9, 25.6]
    assert set(results.tables["robustness_summary"]["Survived"]) == {"9 of 9"}


def test_no_table_contains_donor_ids(results):
    assert all("UserID_clean" not in t.columns for t in results.tables.values())


def test_dashboard_tables_reproduce_every_committed_file(tmp_path):
    prepare_data.prepare(out_dir=tmp_path)
    committed = sorted((ROOT / "data_clean" / "dashboard_data").glob("*.csv"))
    assert len(committed) == 10
    different = [p.name for p in committed if (tmp_path / p.name).read_bytes() != p.read_bytes()]
    assert not different, f"dashboard tables that changed: {different}"


def test_index_html_is_up_to_date_with_its_sources():
    assert build.main(["--check"]) == 0


def test_js_fixtures_are_up_to_date():
    import sys
    sys.path.insert(0, str(ROOT / "tests"))
    import make_fixtures
    stored = json.loads((ROOT / "tests" / "fixtures" / "planner_fixtures.json").read_text(encoding="utf-8"))
    assert make_fixtures.build() == stored


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_javascript_planner_matches_the_python_analysis():
    done = subprocess.run(["node", "--test"], cwd=ROOT, capture_output=True, text=True)
    assert done.returncode == 0, done.stdout[-2000:] + done.stderr[-1000:]
