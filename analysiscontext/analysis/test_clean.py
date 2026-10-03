"""Tests for clean.py outputs. Run clean.py first.

uv run --with pandas --with numpy --with pyarrow --with pytest python -m pytest test_clean.py -q
"""
import hashlib
import json

import pandas as pd
import pytest

import HackYeah2026.analysiscontext.analysis.clean as clean

OUT = clean.OUT


@pytest.fixture(scope="module")
def daily():
    return pd.read_csv(OUT / "daily_clean.csv", parse_dates=["ts_local"])


@pytest.fixture(scope="module")
def participants():
    return json.loads((OUT / "participants.json").read_text())


def test_reference_row_p01(daily):
    """Hand-checked alignment: P01, survey day 2019-11-02 (analiza-pmdata.md 12.9, runda2 9.7)."""
    r = daily[(daily.pid == "p01") & (daily.date == "2019-11-02")]
    assert len(r) == 1
    r = r.iloc[0]
    assert r.ts_local == pd.Timestamp("2019-11-02 11:00:01")
    assert r.sleep_h_lag1 == pytest.approx(6.30, abs=0.01)
    assert r.rhr_night_lag1 == 53
    assert r.steps_lag1 == 17873
    assert r.lightly_lag1 == 245
    assert r.mvpa_lag1 == 130
    assert r.wake_pct_lag1 == pytest.approx(52 / 430 * 100, abs=0.01)
    assert r.rem_pct_lag1 == pytest.approx(83 / 378 * 100, abs=0.01)
    assert r.hr_sleep_mean_lag1 == pytest.approx(54.2, abs=0.1)
    assert r.z_cardio_peak_lag1 == 3


def test_unique_key(daily):
    assert not daily.duplicated(["pid", "date"]).any()


def test_gates_match_output(daily, participants):
    kept = sorted(p for p, v in participants.items() if v["included"])
    assert sorted(daily.pid.unique()) == kept
    assert sorted(set(participants) - set(kept)) == ["p02", "p03", "p12", "p13"]


def test_personas_subset(daily):
    pers = pd.read_csv(OUT / "daily_personas.csv")
    assert set(pers.pid) == set(clean.PERSONAS)
    assert len(pers.merge(daily[["pid", "date"]], on=["pid", "date"])) == len(pers)
    assert set(pers.persona_role) == {"main", "backup"}


def test_no_sleep_after_survey_in_lag1(daily):
    assert daily.loc[daily.sleep_after_survey, [f"{c}_lag1" for c in clean.NIGHT_COLS]].isna().all().all()


def test_valid_ranges(daily):
    for c, (lo, hi) in clean.VALID.items():
        for col in [x for x in daily.columns if x.startswith(c + "_")]:
            v = daily[col].dropna()
            assert v.between(lo, hi).all(), col


def test_stage_features_only_on_stages_nights(daily):
    for c in ["wake_pct_lag1", "rem_pct_lag1", "deep_pct_lag1"]:
        assert daily.loc[daily.sleep_type != "stages", c].isna().all(), c


def test_nonwear_activity_is_nan(daily):
    for c in clean.DAY_COLS:
        assert daily.loc[daily.nonwear_dm1, f"{c}_lag1"].isna().all(), c


def test_label_matches_z(daily):
    z, lab = daily.z, daily.label
    assert (lab[z < -clean.DEAD_ZONE] == "bad").all()
    assert (lab[z > clean.DEAD_ZONE] == "good").all()
    assert (lab[z.abs() <= clean.DEAD_ZONE] == "neutral").all()
    assert lab[z.isna()].isna().all()


def test_label_fit_on_prelockdown(daily):
    """Median-centred z: SD of comp on pre-lockdown labelled days is 1 per person."""
    pre = daily[~daily.post_lockdown & daily.comp.notna()]
    for pid, g in pre.groupby("pid"):
        assert g.z.std(ddof=0) == pytest.approx(1.0, abs=1e-4), pid  # CSV keeps 6 significant digits


def test_analysis_window(daily):
    w = daily[daily.in_analysis_window]
    assert not w.post_lockdown.any()
    assert w.label.notna().all() and w.sleep_h_lag1.notna().all() and w.steps_lag1.notna().all()


def test_deterministic():
    names = ["daily_clean.csv", "daily_personas.csv", "participants.json", "feature_config.json",
             "cleaning_log.csv"]
    h1 = {n: hashlib.sha256((OUT / n).read_bytes()).hexdigest() for n in names}
    clean.build()
    h2 = {n: hashlib.sha256((OUT / n).read_bytes()).hexdigest() for n in names}
    assert h1 == h2
