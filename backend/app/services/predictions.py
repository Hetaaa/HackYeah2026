import datetime as dt
import threading
from collections import OrderedDict

import numpy as np
import pandas as pd
from sqlmodel import Session, select

from app.insights import cleaning
from app.insights import config as C
from app.insights.sources.rows import user_from_rows
from app.models import Day, Persona
from app.schemas import PredictionRead
from app.services.users import today_of
from app.wellness.build_features import LABELS, build_features
from app.wellness.train_predict import predict

CACHE_SIZE = 32
_cache: OrderedDict[tuple, PredictionRead] = OrderedDict()
_lock = threading.Lock()


def historical_labels(table: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Same prefix calibration as add_label, without creating hundreds of DataFrames."""
    values = table[C.LABEL_FIELDS].to_numpy(dtype=float)
    complete = np.isfinite(values).all(axis=1)
    eligible = complete & ~table.outside_window.to_numpy(dtype=bool)
    comps = np.full(len(table), np.nan)
    labels = np.full(len(table), np.nan, dtype=object)
    for i in np.flatnonzero(complete):
        history = values[: i + 1][eligible[: i + 1]]
        comp = float(values[i].mean())
        score = comp - 3
        personal = False
        if len(history) >= C.MIN_LABEL_DAYS:
            median = np.median(history, axis=0)
            sd = history.std(axis=0, ddof=0)
            varying = sd > 0
            deviations = np.zeros_like(history)
            deviations[:, varying] = (history[:, varying] - median[varying]) / sd[varying]
            comp_sd = deviations.mean(axis=1).std(ddof=0)
            if comp_sd > 0:
                current = np.zeros(len(C.LABEL_FIELDS))
                current[varying] = (values[i, varying] - median[varying]) / sd[varying]
                comp = float(current.mean())
                score = comp / comp_sd
                personal = True
        comps[i] = comp
        if personal:
            labels[i] = (
                "bad" if score < -C.DEAD_ZONE else ("good" if score > C.DEAD_ZONE else "neutral")
            )
        else:
            labels[i] = "good" if comp >= 3.5 else ("bad" if comp <= 2.5 else "neutral")
    return comps, labels


def _snapshot(session: Session, persona: Persona, date: dt.date) -> tuple[list[dict], dict]:
    days = session.exec(select(Day).where(Day.date <= date).order_by(Day.user_id, Day.date)).all()
    people = {p.id: p for p in session.exec(select(Persona).order_by(Persona.id)).all()}
    rows = []
    for day in days:
        if day.date == date and day.user_id != persona.id:
            continue
        row = day.model_dump(exclude={"id"})
        if day.date == date:
            row.update(
                {c: None for c in ("mood", "fatigue", "stress", "sleep_quality", "survey_at")}
            )
        rows.append(row)
    return rows, people


def prediction_rows(session: Session, persona: Persona, date: dt.date) -> pd.DataFrame:
    """Use the database only; hide today's answers and all users' future data."""
    rows, people = _snapshot(session, persona, date)
    return _prediction_rows(rows, people, persona, date)


def _prediction_rows(
    days: list[dict], people: dict, persona: Persona, date: dt.date
) -> pd.DataFrame:
    parts = []
    for pid in people:
        rows = [d for d in days if d["user_id"] == pid and d["date"] < date]
        if pid == persona.id:
            current = next(
                (d.copy() for d in days if d["user_id"] == pid and d["date"] == date),
                {"date": date},
            )
            current.update(
                {c: None for c in ("mood", "fatigue", "stress", "sleep_quality", "survey_at")}
            )
            rows.append(current)
        if not rows:
            continue
        window_end = people[pid].analysis_window_end
        table = cleaning.align(
            user_from_rows(pid, rows),
            pd.Timestamp(window_end) if window_end else None,
            all_dates=True,
        )
        # Unanswered days have no survey timestamp in the existing adapter. Use the
        # same morning cutoff as /today, and mask any sleep ending after it (no tolerance).
        sleep_ends = pd.Series(
            {pd.Timestamp(r["date"]): r.get("sleep_end") for r in rows}, dtype=object
        )
        ends = pd.to_datetime(sleep_ends, format="ISO8601").reindex(table.date)
        cutoff = table.ts_local.fillna(table.date + pd.Timedelta(hours=8))
        table["sleep_after_survey"] = ends.to_numpy() > cutoff.to_numpy()
        # Freeze each historical composite/label with only surveys available at that date.
        table["comp"], table["label"] = historical_labels(table)
        table["pid"] = pid
        table["weekday"] = table.date.dt.dayofweek
        table["weekend_Dm1"] = table.weekend_dm1.astype(float)
        table["in_analysis_window"] = (
            ~table.outside_window
            & table.label.notna()
            & table.sleep_h_lag1.notna()
            & table.steps_lag1.notna()
        )
        if pid == persona.id:
            table.loc[table.date.eq(pd.Timestamp(date)), "in_analysis_window"] = True
        parts.append(table)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def get_prediction(session: Session, persona: Persona) -> PredictionRead:
    date = today_of(persona)
    rows, people = _snapshot(session, persona, date)
    key = (
        persona.id,
        date,
        tuple((pid, p.analysis_window_end) for pid, p in people.items()),
        tuple(tuple(row.items()) for row in rows),
    )
    # Sync FastAPI routes run in a threadpool. One computation per data version.
    with _lock:
        cached = _cache.get(key)
        if cached is not None:
            _cache.move_to_end(key)
            return cached.model_copy(deep=True)
        result = _compute_prediction(rows, people, persona, date)
        _cache[key] = result
        if len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
        return result.model_copy(deep=True)


def _compute_prediction(
    rows: list[dict], people: dict, persona: Persona, date: dt.date
) -> PredictionRead:
    raw = _prediction_rows(rows, people, persona, date)
    features = build_features(raw, keep_unlabeled=True)
    train = features[features.date.lt(pd.Timestamp(date)) & features.label.notna()]
    test = features[features.pid.eq(persona.id) & features.date.eq(pd.Timestamp(date))]
    if train.empty or test.empty:
        return PredictionRead(date=date, status="insufficient_history", training_days=len(train))
    probabilities = predict(train, test, persona.id)[0]
    names = list(LABELS)
    return PredictionRead(
        date=date,
        status="ok",
        training_days=len(train),
        pred=names[int(np.argmax(probabilities))],
        p_bad=float(probabilities[0]),
        p_neutral=float(probabilities[1]),
        p_good=float(probabilities[2]),
    )
