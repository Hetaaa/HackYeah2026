"""Regression on the real PMData files. Skipped unless PMDATA_DIR points at the dataset root.

PMDATA_DIR=../../pmdata uv run pytest tests/test_insights_pmdata.py
"""

import os
from pathlib import Path

import pytest

from app.insights import cleaning
from app.insights import config as C
from app.insights.analyze import analyze_user
from app.insights.sources import pmdata

ROOT = Path(os.environ.get("PMDATA_DIR", "/nonexistent"))
pytestmark = pytest.mark.skipif(not (ROOT / "p01").exists(), reason="PMDATA_DIR not set")
CACHE = Path(".cache/insights")


def test_reference_row_p01() -> None:
    """Hand-checked alignment for P01, survey day 2019-11-02."""
    table, _ = cleaning.build_table(pmdata.load_user(ROOT, "p01", CACHE), C.PMDATA_WINDOW_END)
    r = table[table.date == "2019-11-02"].iloc[0]

    assert r.sleep_h_lag1 == pytest.approx(6.30, abs=0.01)
    assert r.rhr_night_lag1 == 53
    assert r.steps_lag1 == 17873
    assert r.lightly_lag1 == 245
    assert r.mvpa_lag1 == 130
    assert r.wake_pct_lag1 == pytest.approx(52 / 430 * 100, abs=0.01)
    assert r.rem_pct_lag1 == pytest.approx(83 / 378 * 100, abs=0.01)
    assert r.hr_sleep_mean_lag1 == pytest.approx(54.2, abs=0.1)
    assert r.z_cardio_peak_lag1 == 3


@pytest.mark.parametrize(
    ("pid", "kind", "feature", "op", "threshold"),
    [
        ("p01", "bad", "z_cardio_peak", "above", 10),
        ("p06", "good", "sleep_h", "above", 6.5),
        ("p10", "bad", "wake_pct", "above", 12),
        ("p10", "good", "lightly", "above", 320),
        ("p16", "bad", "sleep_h", "below", 6),
    ],
)
def test_validated_persona_patterns(
    pid: str, kind: str, feature: str, op: str, threshold: float
) -> None:
    result = analyze_user(pmdata.load_user(ROOT, pid, CACHE), C.PMDATA_WINDOW_END)
    best = result["patterns"][kind]["patterns"][0]

    assert (best["feature"], best["op"], best["threshold"]) == (feature, op, threshold)
    assert best["level"] == "significant"
