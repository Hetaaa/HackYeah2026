"""Export PMData demo personas to CSV (data/demo/), which the seed loads on startup.

Raw PMData stays outside the repo; this turns the Fitbit export + wellness answers of the
chosen participants into Day rows through the same Fitbit adapter the real watch sync uses.
Each persona gets a demo "today" (see pick_today): days after it are dropped and its
check-in is left empty so it can be filled live; the real answers go to demo_answers.

Run with: uv run python -m scripts.import_pmdata ../../pmdata [--all]
  --all  export every participant, not only the personas
"""

import argparse
import csv
from pathlib import Path

import pandas as pd

from app.insights import cleaning
from app.insights import config as C
from app.insights.analyze import analyze_user
from app.insights.sources import pmdata
from app.insights.sources.rows import user_from_rows

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "demo"
CACHE = Path(".cache/insights")
SURVEY = ["mood", "fatigue", "sleep_quality", "stress"]
LABEL_FIELDS = ["mood", "fatigue", "stress"]  # sleep_quality is collected but not in the label
MIN_HISTORY_DAYS = 90  # "today" late enough for a rich calendar
SAFE_SCORE = 0.8  # label threshold is 0.5: a margin against a slider slip
NIGHT = {  # Day column -> nights column
    "sleep_end": "end",
    "sleep_type": "sleep_type",
    "sleep_efficiency": "sleep_eff",
    "wake_minutes": "wake_min",
    "wake_pct": "wake_pct",
    "rem_pct": "rem_pct",
    "deep_pct": "deep_pct",
    "sleep_hr_mean": "hr_sleep_mean",
    "sleep_score": "ss_overall",
    "resting_hr": "rhr_night",
}
ACTIVITY = {  # Day column -> days column
    "steps": "steps",
    "active_minutes": "mvpa",
    "light_minutes": "lightly",
    "sedentary_minutes": "sedentary",
    "cardio_peak_minutes": "z_cardio_peak",
    "wear_minutes": "wear_min",
    "wear_minutes_day": "wear_day",
}
COLUMNS = [
    "user_id",
    "date",
    "sleep_minutes",
    "sleep_start",
    "time_in_bed_minutes",
    *NIGHT,
    *ACTIVITY,
    *SURVEY,
    "survey_at",
]


def _fmt(value: object) -> str:
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return ""
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def day_rows(root: Path, pid: str) -> list[dict[str, str]]:
    user = pmdata.load_user(root, pid, CACHE)
    nights, days = user.nights, user.days
    surveys = cleaning.surveys_by_day(user.surveys).set_index("date")
    dates = nights.index.union(days.index).union(surveys.index)
    rows = []
    for date in dates:
        row: dict[str, object] = {"user_id": pid, "date": date.date().isoformat()}
        if date in nights.index:
            n = nights.loc[date]
            row["sleep_minutes"] = n.sleep_h * 60
            row["time_in_bed_minutes"] = n.time_in_bed_h * 60
            row["sleep_start"] = date - pd.Timedelta(hours=6) + pd.Timedelta(hours=n.bedtime_h)
            row |= {col: n[src] for col, src in NIGHT.items()}
        if date in days.index:
            row |= {col: days.loc[date, src] for col, src in ACTIVITY.items()}
        if date in surveys.index:
            s = surveys.loc[date]
            row |= {f: (None if pd.isna(s[f]) else int(s[f])) for f in SURVEY}
            local = pd.Timestamp(s.ts_local).tz_localize(C.TZ)
            row["survey_at"] = local.tz_convert("UTC")
        rows.append({c: _fmt(row.get(c)) for c in COLUMNS})
    return rows


def _analyze(pid: str, rows: list[dict[str, str]]) -> dict:
    data = [{k: (v or None) for k, v in r.items()} for r in rows]
    return analyze_user(user_from_rows(pid, data), C.PMDATA_WINDOW_END, all_dates=True)


def _story_kind(result: dict) -> str | None:
    """The persona's story: bad-day patterns if it has significant ones, else the recipe."""
    for kind in ("bad", "good"):
        if any(p["level"] == "significant" for p in result["patterns"][kind]["patterns"]):
            return kind
    return None


def _key(p: dict) -> tuple:
    return p["feature"], p["variant"], p["op"], p["threshold"]


def _nudged(answers: dict[str, str]) -> list[dict[str, str]]:
    """The answers with one of mood / fatigue / stress moved by 1 (a slider slip on stage)."""
    out = []
    for field in LABEL_FIELDS:
        for step in (-1, 1):
            value = min(5, max(1, int(answers[field]) + step))
            if str(value) != answers[field]:
                out.append(answers | {field: str(value)})
    return out


def _candidates(pid: str, rows: list[dict[str, str]], kind: str):
    """Days (latest first) whose morning heads-up and check-in tell the persona's story:
    a significant pattern is triggered before the check-in, the real answers give the matching
    label with that same pattern as the reason, and it stays significant with the day added.
    Yields (index, answers, score)."""
    min_date = (pd.Timestamp(rows[0]["date"]) + pd.Timedelta(days=MIN_HISTORY_DAYS)).date()
    end = (C.PMDATA_WINDOW_END - pd.Timedelta(days=1)).date().isoformat()
    for i in range(len(rows) - 1, -1, -1):
        today = rows[i]
        if today["date"] > end or today["date"] < min_date.isoformat():
            continue
        if not all(today[f] for f in SURVEY):
            continue
        before = rows[:i] + [today | dict.fromkeys([*SURVEY, "survey_at"], "")]
        signals = _analyze(pid, before)["days"][-1]["signals"][kind]
        if not signals:
            continue
        after = _analyze(pid, rows[: i + 1])
        day = after["days"][-1]
        reason = day["reasons"][0]["feature"] if day["reasons"] else None
        if day["label"] == kind and reason == signals[0]["feature"] and _story_kind(after) == kind:
            yield i, {f: today[f] for f in SURVEY}, day["score"]


def pick_today(pid: str, rows: list[dict[str, str]]) -> tuple[str, dict[str, str], str] | None:
    """Latest story day, preferring days that are safe against a slider slip on stage:

    1. "robust": the label survives any one of mood / fatigue / stress being off by 1,
    2. "margin": the check-in score is clearly past the label threshold (|score| >= 0.8),
    3. "exact": only the exact real answers give the story (prefill them in the UI).
    Returns (date, real answers, tier) or None.
    """
    kind = _story_kind(_analyze(pid, rows))
    if kind is None:
        return None
    found = list(_candidates(pid, rows, kind))
    for i, answers, _ in found:
        nudges = _nudged(answers)
        if all(
            _analyze(pid, rows[:i] + [rows[i] | n])["days"][-1]["label"] == kind for n in nudges
        ):
            return rows[i]["date"], answers, "robust"
    for i, answers, score in found:
        if abs(score) >= SAFE_SCORE:
            return rows[i]["date"], answers, "margin"
    if found:
        i, answers, _ = found[0]
        return rows[i]["date"], answers, "exact"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pmdata", type=Path)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    pids = pmdata.PIDS if args.all else list(C.PERSONAS)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    personas, days = [], []
    for position, pid in enumerate(pids):
        rows = day_rows(args.pmdata, pid)
        picked = pick_today(pid, rows)
        today, answers, tier = picked if picked else (rows[-1]["date"], None, "none")
        # the demo ends "today": later days are dropped, today's check-in is left to fill live
        rows = [r for r in rows if r["date"] <= today]
        if answers:
            rows[-1] |= dict.fromkeys([*SURVEY, "survey_at"], "")
        days += rows
        persona = C.PERSONAS.get(pid)
        name, last_name, description = (
            (persona.name, persona.last_name, persona.tagline) if persona else (pid.upper(), "", "")
        )
        personas.append(
            {
                "id": pid,
                "name": name,
                "last_name": last_name,
                "description": description,
                "analysis_window_end": C.PMDATA_WINDOW_END.date().isoformat(),
                "demo_today": today,
                "demo_answers": ",".join(answers[f] for f in SURVEY) if answers else "",
                "position": position,
            }
        )
        print(f"{pid}: today {today} ({tier}), answers {answers}, {len(rows)} days")
    with (OUT_DIR / "personas.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(personas[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(personas)
    with (OUT_DIR / "days.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(days)
    print(f"Wrote {len(pids)} personas, {len(days)} days to {OUT_DIR}")


if __name__ == "__main__":
    main()
