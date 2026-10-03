"""Export PMData demo personas to CSV (data/demo/), which the seed loads on startup.

Raw PMData stays outside the repo; this turns the Fitbit export + wellness answers of the
chosen participants into Day rows through the same Fitbit adapter the real watch sync uses.

Run with: uv run python -m scripts.import_pmdata ../../pmdata [--all]
  --all  export every participant, not only the personas
"""

import argparse
import csv
from pathlib import Path

import pandas as pd

from app.insights import cleaning
from app.insights import config as C
from app.insights.sources import pmdata

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "demo"
CACHE = Path(".cache/insights")
SURVEY = ["mood", "fatigue", "sleep_quality", "stress"]
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pmdata", type=Path)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    pids = pmdata.PIDS if args.all else list(C.PERSONAS)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with (OUT_DIR / "personas.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "name", "description", "analysis_window_end"])
        for pid in pids:
            persona = C.PERSONAS.get(pid)
            name, description = (persona.name, persona.tagline) if persona else (pid.upper(), "")
            writer.writerow([pid, name, description, C.PMDATA_WINDOW_END.date().isoformat()])
    with (OUT_DIR / "days.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=COLUMNS)
        writer.writeheader()
        total = 0
        for pid in pids:
            rows = day_rows(args.pmdata, pid)
            writer.writerows(rows)
            total += len(rows)
    print(f"Wrote {len(pids)} personas, {total} days to {OUT_DIR}")


if __name__ == "__main__":
    main()
