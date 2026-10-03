"""Wear time per day from fitbit/heart_rate.json (heavy, run once).

Wear minutes = number of distinct local minutes on a calendar day with >=1 HR reading.
Uses a regex scan over raw bytes instead of json.load (1.5M dicts per file would be
several GB of RAM). Processes participants one at a time.

Output: cache/wear_minutes.csv  (pid, date, wear_min, wear_min_night [00-06], hr_readings)
"""
import re
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent / "pmdata"
OUT = Path(__file__).resolve().parent / "cache" / "wear_minutes.csv"
PAT = re.compile(rb'"dateTime": "(\d{4}-\d\d-\d\d) (\d\d):(\d\d)')


def wear_for(pid: str) -> pd.DataFrame:
    raw = (ROOT / pid / "fitbit" / "heart_rate.json").read_bytes()
    minutes = set()
    readings = Counter()
    for m in PAT.finditer(raw):
        d, h, mi = m.group(1), m.group(2), m.group(3)
        minutes.add((d, h, mi))
        readings[d] += 1
    del raw
    per_day = Counter()
    per_night = Counter()
    for d, h, _ in minutes:
        per_day[d] += 1
        if int(h) < 6:
            per_night[d] += 1
    rows = [
        dict(pid=pid, date=d.decode(), wear_min=per_day[d],
             wear_min_night=per_night.get(d, 0), hr_readings=readings[d])
        for d in sorted(per_day)
    ]
    return pd.DataFrame(rows)


def main():
    pids = sys.argv[1:] or [f"p{i:02d}" for i in range(1, 17)]
    frames = []
    if OUT.exists():
        old = pd.read_csv(OUT)
        frames.append(old[~old.pid.isin(pids)])
    for pid in pids:
        df = wear_for(pid)
        print(pid, len(df), "days, median wear", df.wear_min.median(), flush=True)
        frames.append(df)
    out = pd.concat(frames).sort_values(["pid", "date"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print("wrote", OUT, len(out))


if __name__ == "__main__":
    main()
