import numpy as np
import pandas as pd

from app.wellness.build_features import FEATURES, build_features
from app.wellness.train_predict import blocks, predict


def daily() -> pd.DataFrame:
    n = 40
    return pd.DataFrame(
        {
            "pid": ["p01"] * n,
            "date": pd.date_range("2020-01-01", periods=n),
            "label": ["bad", "neutral", "good", "neutral"] * 10,
            "comp": np.sin(np.arange(n)),
            "mood": np.arange(n) % 5 + 1,
            "fatigue": 3,
            "stress": 2,
            "sleep_quality": 4,
            "sleep_h_lag1": 6 + np.arange(n) % 3,
            "mvpa_lag1": np.arange(n),
            "in_analysis_window": True,
        }
    )


def test_future_and_same_day_survey_do_not_change_features_or_predictions():
    raw = daily()
    features = build_features(raw)
    changed = raw.copy()
    changed.loc[20:, ["mood", "fatigue", "stress", "sleep_quality", "comp"]] = 999
    changed.loc[21:, "sleep_h_lag1"] = 100
    changed.loc[20:, "label"] = "bad"
    perturbed = build_features(changed)
    pd.testing.assert_frame_equal(features.loc[:20, FEATURES], perturbed.loc[:20, FEATURES])
    np.testing.assert_allclose(
        predict(features.iloc[:20], features.iloc[[20]], "p01"),
        predict(perturbed.iloc[:20], perturbed.iloc[[20]], "p01"),
    )


def test_blocks_exclude_cut_date_and_future_for_all_users():
    raw = daily()
    other = raw.assign(pid="p02", date=raw.date + pd.Timedelta(days=5))
    features = build_features(pd.concat([raw, other]))
    for _, cut, train, test in blocks(features):
        assert (train.date < cut).all()
        assert (test.date >= cut).all()


def test_every_row_matches_prefix_with_its_survey_hidden():
    raw = daily()
    features = build_features(raw)
    for i in range(len(raw)):
        prefix = raw.iloc[: i + 1].copy()
        prefix.loc[i, ["mood", "fatigue", "stress", "sleep_quality", "comp"]] = -99
        prefix.loc[i, "label"] = "neutral"
        pd.testing.assert_series_equal(
            features.loc[i, FEATURES], build_features(prefix).loc[i, FEATURES]
        )


def test_missing_training_classes_have_zero_probability():
    features = build_features(daily())
    train = features[features.label.ne(1)]
    probabilities = predict(train, features.iloc[[20]], "p01")
    assert probabilities[0, 1] == 0
    np.testing.assert_allclose(probabilities.sum(axis=1), 1, atol=1e-6)


def test_gap_and_sleep_safeguard():
    raw = daily().drop(index=18).reset_index(drop=True)
    raw["sleep_after_survey"] = False
    raw.loc[19, "sleep_after_survey"] = True
    features = build_features(raw)
    assert pd.isna(features.loc[18, "label_y"])
    assert pd.isna(features.loc[19, "sleep_h_lag1"])
    assert pd.isna(features.loc[19, "sleep_vs_norm"])
    assert build_features(raw, safeguard=False).loc[19, "sleep_h_lag1"] > 0


def test_prediction_api_missing_user_and_empty_history(client, session):
    from app.models import Persona

    assert client.get("/api/users/missing/today/prediction").status_code == 404
    session.add(Persona(id="new", name="New"))
    session.commit()
    response = client.get("/api/users/new/today/prediction")
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_history"
    assert response.json()["pred"] is None


def test_backend_prediction_ignores_today_survey_and_future(client, demo):
    import datetime as dt

    from sqlmodel import select

    from app.models import Day, Persona

    persona = demo.get(Persona, "p01")
    endpoint = "/api/users/p01/today/prediction"
    before = client.get(endpoint)
    assert before.status_code == 200
    assert before.json()["status"] == "ok"
    assert abs(sum(before.json()[c] for c in ("p_bad", "p_neutral", "p_good")) - 1) < 1e-6
    row = demo.exec(
        select(Day).where(Day.user_id == persona.id, Day.date == persona.demo_today)
    ).one()
    row.mood, row.fatigue, row.stress, row.sleep_quality = 1, 5, 1, 5
    demo.add(row)
    demo.add(
        Day(
            user_id=persona.id,
            date=persona.demo_today + dt.timedelta(days=500),
            mood=5,
            fatigue=5,
            stress=5,
            sleep_quality=5,
            steps=99999,
        )
    )
    demo.commit()
    assert client.get(endpoint).json() == before.json()


def test_backend_masks_sleep_ending_after_morning_cutoff(session):
    import datetime as dt

    from app.models import Day, Persona
    from app.services.predictions import prediction_rows

    date = dt.date(2020, 1, 2)
    persona = Persona(id="p01", name="User", demo_today=date)
    session.add(persona)
    session.add(
        Day(
            user_id=persona.id,
            date=date,
            sleep_minutes=480,
            sleep_end=dt.datetime(2020, 1, 2, 9),
            sleep_score=90,
        )
    )
    session.commit()
    features = build_features(prediction_rows(session, persona, date), keep_unlabeled=True)
    assert features["sleep_h_lag1"].isna().all()
    assert features["ss_overall_lag1"].isna().all()


def test_fast_calibration_matches_original_prefix_algorithm():
    from app.insights import cleaning
    from app.services.predictions import historical_labels

    rng = np.random.default_rng(4)
    for constant in (False, True):
        values = rng.integers(1, 6, size=(100, 3)).astype(float)
        if constant:
            values[:] = 3
        else:
            values[3, 0] = np.nan
            values[:, 1] = 3  # constant dimension in a varying history
        table = pd.DataFrame(values, columns=["mood", "fatigue", "stress"])
        table["outside_window"] = np.arange(100) >= 70
        comp, labels = historical_labels(table)
        expected_comp, expected_labels = [], []
        for i in range(len(table)):
            prefix = table.iloc[: i + 1].copy()
            cleaning.add_label(prefix)
            expected_comp.append(prefix.comp.iloc[-1])
            expected_labels.append(prefix.label.iloc[-1])
        np.testing.assert_allclose(comp, expected_comp, atol=1e-12, equal_nan=True)
        pd.testing.assert_series_equal(pd.Series(labels), pd.Series(expected_labels))


def test_prediction_cache_reuses_results_and_invalidates_on_relevant_data(demo, monkeypatch):
    from sqlmodel import select

    from app.models import Day, Persona
    from app.services import predictions

    predictions._cache.clear()
    original = predictions._compute_prediction
    calls = []

    def counted(*args):
        calls.append(1)
        return original(*args)

    monkeypatch.setattr(predictions, "_compute_prediction", counted)
    persona = demo.get(Persona, "p01")
    first = predictions.get_prediction(demo, persona)
    second = predictions.get_prediction(demo, persona)
    assert first == second
    assert len(calls) == 1
    # Returning a response must not allow callers to mutate the cached object.
    first.pred = "neutral" if first.pred == "bad" else "bad"
    assert predictions.get_prediction(demo, persona) == second
    row = demo.exec(
        select(Day).where(Day.user_id == persona.id, Day.date == persona.demo_today)
    ).one()
    row.mood = 1
    demo.add(row)
    demo.commit()
    assert predictions.get_prediction(demo, persona) == second
    assert len(calls) == 1
    row.steps = (row.steps or 0) + 100
    demo.add(row)
    demo.commit()
    predictions.get_prediction(demo, persona)
    assert len(calls) == 2
    history = demo.exec(
        select(Day).where(Day.user_id == "p06", Day.date < persona.demo_today).order_by(Day.date)
    ).first()
    history.mood = 1 if history.mood != 1 else 5
    demo.add(history)
    demo.commit()
    predictions.get_prediction(demo, persona)
    assert len(calls) == 3
