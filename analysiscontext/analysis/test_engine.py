"""Tests for engine.py / reasons.py. Run clean.py and reasons.py first.

uv run --with pandas --with numpy --with pytest python -m pytest test_engine.py -q
"""
import json

import numpy as np
import pandas as pd
import pytest

from HackYeah2026.analysiscontext.analysis.engine import OUT, Settings, analysis_rows, load, run_person, scores, search_features, wilson_lower


@pytest.fixture(scope="module")
def data():
    return load()


@pytest.fixture(scope="module")
def patterns():
    return json.loads((OUT / "patterns.json").read_text())


@pytest.fixture(scope="module")
def calendar():
    return json.loads((OUT / "calendar.json").read_text())


def test_wilson_lower():
    assert wilson_lower(np.array([3.0]), np.array([3.0]))[0] < wilson_lower(np.array([10.0]), np.array([13.0]))[0]
    assert wilson_lower(np.array([0.0]), np.array([10.0]))[0] == pytest.approx(0, abs=1e-12)


def test_support_and_cover_rules():
    s = Settings()
    n = 40
    IN = np.zeros((3, n), bool)
    IN[0, :5] = True  # too few days in condition
    IN[1, :25] = True  # covers > 50 %
    IN[2, :15] = True  # ok
    VALID = np.ones((3, n), bool)
    y = np.zeros(n, bool)
    y[:10] = True
    sc = scores(IN, VALID, y, s)
    assert np.isneginf(sc[0]) and np.isneginf(sc[1]) and np.isfinite(sc[2])


def test_engine_deterministic(data):
    daily, participants, config = data
    rows = analysis_rows(daily, "p10")
    feats = search_features(config, participants["p10"]["group_E_feature"], Settings())
    y = rows.label.to_numpy() == "bad"
    assert run_person(rows, y, feats, "bad", Settings()) == run_person(rows, y, feats, "bad", Settings())


def test_group_e_per_participant(data):
    _, participants, config = data
    for info in participants.values():
        feats = search_features(config, info["group_E_feature"], Settings())
        assert info["group_E_feature"] in feats
        assert {"mvpa", "z_cardio_peak"} - {info["group_E_feature"]} & set(feats) == set()


def test_pattern_counts_consistent(data, patterns):
    daily, _, _ = data
    for pid, r in patterns.items():
        rows = analysis_rows(daily, pid)
        for kind in ("bad", "good"):
            assert len(r[kind]["patterns"]) <= 3
            for p in r[kind]["patterns"]:
                x = rows[p["column"]].to_numpy(float)
                v = ~np.isnan(x)
                cond = ((x < p["threshold"]) if p["op"] == "below" else (x > p["threshold"])) & v
                assert cond.sum() == p["days_in_condition"]
                assert (rows.label.to_numpy()[cond] == kind).sum() == p["target_days_in_condition"]
                assert p["days_in_condition"] >= 10 and p["days_in_condition"] <= 0.5 * v.sum()


def test_personas_have_significant_patterns(patterns):
    for pid in ("p01", "p06", "p10"):
        sig = [p for k in ("bad", "good") for p in patterns[pid][k]["patterns"] if p["level"] == "significant"]
        assert sig, pid


def test_calendar_reasons(calendar, patterns):
    for pid, c in calendar.items():
        for d in c["days"]:
            if d["label"] not in ("bad", "good"):
                assert d["reasons"] == []
                continue
            src = [r["source"] for r in d["reasons"]]
            assert 1 <= len(src) <= 2
            if "pattern" in src:
                assert set(src) == {"pattern"}
                cols = {p["column"] for p in patterns[pid][d["label"]]["patterns"] if p["level"] == "significant"}
                assert {r["column"] for r in d["reasons"]} <= cols
            else:
                assert src == ["none"]


def test_calendar_covers_all_days(data, calendar):
    daily, _, _ = data
    for pid, c in calendar.items():
        assert len(c["days"]) == (daily.pid == pid).sum()
        assert pd.Series([d["date"] for d in c["days"]]).is_monotonic_increasing


def test_calendar_compare(calendar):
    for c in calendar.values():
        for d in c["days"]:
            assert len(d["compare"]) <= 2
            zs = [abs(x["z"]) for x in d["compare"]]
            assert all(z >= 1 for z in zs) and zs == sorted(zs, reverse=True)
            ref = "average good day" if c["norm_source"] == "good_days" else "average day"
            assert all(ref in x["text"] for x in d["compare"])
