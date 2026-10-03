"""Validation of the pattern engine on cleaned data (koncepcja-analityczna.md sec. 5).

1. False positives on null labels (target: <= ~5% of runs with any significant pattern, per kind):
   - shuffle : labels randomly permuted within the person (R runs, fixed seed)
   - swap    : labels of ANOTHER participant (real autocorrelation, unrelated to this person's data),
               truncated / tiled to length
2. Real data under setting variants (to check post-hoc decisions):
   frozen (max_cover 0.5, wake_pct) / no_cover_limit (max_cover 1.0) / sleep_eff (group C = sleep_eff)
3. Split-half: patterns (significant or preliminary) found on the first half of the window, checked on
   the second half (same column, side, threshold): does rate_in > rate_out hold? And vice versa.
4. Weekday check: every significant pattern re-evaluated on days whose D-1 is a weekday only.
5. Injected effect: on each person's real features, labels re-drawn so that nights under 6 h give a bad day
   with p=0.7 and other nights with p=0.2 (R runs); does the engine find sleep_h below ~6 h?

Usage: uv run --with pandas --with numpy python validate.py [--runs 100]
       -> output/validation.json, output/validation.md
"""
from __future__ import annotations

import argparse
import json
from dataclasses import replace

import numpy as np

from HackYeah2026.analysiscontext.analysis.engine import OUT, Settings, analysis_rows, candidates, load, run_person, search_features

SETTINGS = {
    "frozen": Settings(),
    "no_cover_limit": Settings(max_cover=1.0),
    "sleep_eff": Settings(group_c="sleep_eff"),
}


def kinds(info):
    return [k for k in ("bad", "good") if info[f"{k}_patterns_enabled"]]


def has_sig(r):
    return any(p["level"] == "significant" for p in r["patterns"])


def null_fpr(daily, participants, config, s: Settings, runs: int, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    kept = [p for p, v in participants.items() if v["included"]]
    rows = {p: analysis_rows(daily, p) for p in kept}
    labels = {p: rows[p].label.to_numpy() for p in kept}
    res = {"shuffle": {"bad": [0, 0], "good": [0, 0]}, "swap": {"bad": [0, 0], "good": [0, 0]}}
    per_person = {}
    for pid in kept:
        info = participants[pid]
        feats = search_features(config, info["group_E_feature"], s)
        hits = {"bad": 0, "good": 0}
        for kind in kinds(info):
            for _ in range(runs):
                y = rng.permutation(labels[pid]) == kind
                h = has_sig(run_person(rows[pid], y, feats, kind, s))
                res["shuffle"][kind][0] += h
                res["shuffle"][kind][1] += 1
                hits[kind] += h
            for other in kept:
                if other == pid:
                    continue
                src = labels[other]
                y = np.resize(src, len(rows[pid])) == kind
                if y.sum() < 10:
                    continue
                h = has_sig(run_person(rows[pid], y, feats, kind, s))
                res["swap"][kind][0] += h
                res["swap"][kind][1] += 1
        per_person[pid] = {k: round(hits[k] / runs, 3) for k in kinds(info)}
    rates = {m: {k: {"hits": v[0], "runs": v[1], "rate": round(v[0] / v[1], 4) if v[1] else None}
                 for k, v in d.items()} for m, d in res.items()}
    return {"rates": rates, "shuffle_per_person": per_person}


def real_patterns(daily, participants, config, s: Settings) -> dict:
    out = {}
    for pid, info in participants.items():
        if not info["included"]:
            continue
        rows = analysis_rows(daily, pid)
        feats = search_features(config, info["group_E_feature"], s)
        for kind in kinds(info):
            r = run_person(rows, rows.label.to_numpy() == kind, feats, kind, s)
            sig = [f"{p['column']} {p['op']} {p['threshold']:g} ({p['target_days_in_condition']}/"
                   f"{p['days_in_condition']}, p={p['p_global']})"
                   for p in r["patterns"] if p["level"] == "significant"]
            if sig:
                out.setdefault(pid, {})[kind] = sig
    return out


def check_on(rows, p, kind) -> dict | None:
    x = rows[p["column"]].to_numpy(float)
    v = ~np.isnan(x)
    cond = ((x < p["threshold"]) if p["op"] == "below" else (x > p["threshold"])) & v
    y = rows.label.to_numpy() == kind
    n_in, n_out = cond.sum(), (v & ~cond).sum()
    if n_in < 3 or n_out < 3:
        return None
    return {"rate_in": round(float(y[cond].mean()), 3), "rate_out": round(float(y[v & ~cond].mean()), 3),
            "n_in": int(n_in), "replicates": bool(y[cond].mean() > y[v & ~cond].mean())}


def split_half(daily, participants, config, s: Settings) -> dict:
    s_half = replace(s, min_support=7)  # half the data: smaller support so anything can be found
    found, rep, details = 0, 0, []
    for pid, info in participants.items():
        if not info["included"]:
            continue
        rows = analysis_rows(daily, pid)
        h = len(rows) // 2
        halves = (rows.iloc[:h].reset_index(drop=True), rows.iloc[h:].reset_index(drop=True))
        feats = search_features(config, info["group_E_feature"], s)
        for a, b, tag in ((0, 1, "1->2"), (1, 0, "2->1")):
            for kind in kinds(info):
                r = run_person(halves[a], halves[a].label.to_numpy() == kind, feats, kind, s_half)
                for p in r["patterns"]:
                    c = check_on(halves[b], p, kind)
                    if c is None:
                        continue
                    found += 1
                    rep += c["replicates"]
                    details.append({"pid": pid, "dir": tag, "kind": kind, "level": p["level"],
                                    "pattern": f"{p['column']} {p['op']} {p['threshold']:g}",
                                    "train": f"{p['rate_in']:.2f} vs {p['rate_out']:.2f}",
                                    "test": f"{c['rate_in']:.2f} vs {c['rate_out']:.2f} (n_in {c['n_in']})",
                                    "replicates": c["replicates"]})
    return {"patterns_checked": found, "replicated": rep,
            "replication_rate": round(rep / found, 3) if found else None, "details": details}


def weekday_check(daily, participants, config) -> list[dict]:
    out = []
    for pid, info in participants.items():
        if not info["included"]:
            continue
        rows = analysis_rows(daily, pid)
        feats = search_features(config, info["group_E_feature"], Settings())
        wk = rows[~rows.weekend_Dm1].reset_index(drop=True)
        for kind in kinds(info):
            r = run_person(rows, rows.label.to_numpy() == kind, feats, kind, Settings())
            for p in r["patterns"]:
                if p["level"] != "significant":
                    continue
                c = check_on(wk, p, kind)
                out.append({"pid": pid, "kind": kind, "pattern": f"{p['column']} {p['op']} {p['threshold']:g}",
                            "all_days": f"{p['rate_in']:.2f} vs {p['rate_out']:.2f}",
                            "weekdays": f"{c['rate_in']:.2f} vs {c['rate_out']:.2f} (n_in {c['n_in']})" if c else "n/a",
                            "holds": bool(c and c["replicates"])})
    return out


def injected(daily, participants, config, runs: int, seed: int = 1) -> dict:
    rng = np.random.default_rng(seed)
    found = near = total = 0
    for pid, info in participants.items():
        if not info["included"]:
            continue
        rows = analysis_rows(daily, pid)
        x = rows.sleep_h_lag1.to_numpy(float)
        short = x < 6
        if short.sum() < 10 or (~short).sum() < 10:
            continue  # the planted rule cannot be supported for this person
        feats = search_features(config, info["group_E_feature"], Settings())
        for _ in range(runs):
            y = rng.random(len(rows)) < np.where(short, 0.7, 0.2)
            r = run_person(rows, y, feats, "bad", Settings())
            hit = [p for p in r["patterns"] if p["level"] == "significant" and p["feature"] == "sleep_h"]
            total += 1
            found += bool(hit)
            near += bool(hit and hit[0]["op"] == "below" and abs(hit[0]["threshold"] - 6) <= 0.5)
    return {"runs": total, "found_rate": round(found / total, 3) if total else None,
            "threshold_within_0.5h_rate": round(near / total, 3) if total else None}


def main(runs: int):
    daily, participants, config = load()
    n_cand = {}
    for pid, info in participants.items():
        if info["included"]:
            rows = analysis_rows(daily, pid)
            feats = search_features(config, info["group_E_feature"], Settings())
            n_cand[pid] = len(candidates(rows, feats, "bad")[0])
    result = {"runs_per_person": runs, "n_candidates_bad": n_cand, "settings": {}}
    for name, s in SETTINGS.items():
        print("setting", name, flush=True)
        result["settings"][name] = {"null": null_fpr(daily, participants, config, s, runs),
                                    "real_significant": real_patterns(daily, participants, config, s)}
    result["split_half"] = split_half(daily, participants, config, Settings())
    result["weekday_check"] = weekday_check(daily, participants, config)
    result["injected"] = injected(daily, participants, config, max(runs // 5, 10))
    (OUT / "validation.json").write_text(json.dumps(result, indent=2, sort_keys=True))
    write_md(result)


def write_md(r: dict):
    L = ["# Walidacja silnika wzorców", "",
         f"Null: {r['runs_per_person']} permutacji etykiet na osobę + podmiana etykiet innej osoby. "
         "Wskaźnik = odsetek przebiegów z ≥ 1 istotnym wzorcem (cel ≤ ~5% na rodzaj).", "",
         "| ustawienie | shuffle bad | shuffle good | swap bad | swap good | osoby z istotnym wzorcem (prawdziwe etykiety) |",
         "| --- | --: | --: | --: | --: | --: |"]
    for name, d in r["settings"].items():
        n = d["null"]["rates"]
        L.append(f"| {name} | {n['shuffle']['bad']['rate']:.1%} | {n['shuffle']['good']['rate']:.1%} | "
                 f"{n['swap']['bad']['rate']:.1%} | {n['swap']['good']['rate']:.1%} | "
                 f"{len(d['real_significant'])} |")
    L += ["", "## Istotne wzorce na prawdziwych etykietach", ""]
    for name, d in r["settings"].items():
        L.append(f"**{name}**")
        L.append("")
        for pid, k in d["real_significant"].items():
            for kind, pats in k.items():
                L.append(f"- {pid} {kind}: " + "; ".join(pats))
        L.append("")
    sh = r["split_half"]
    L += ["## Split-half", "",
          f"Wzorce z jednej połowy okna sprawdzone na drugiej: {sh['replicated']}/{sh['patterns_checked']} "
          f"zachowuje kierunek (rate_in > rate_out), czyli {sh['replication_rate']:.0%}.", "",
          "| osoba | kierunek | rodzaj | poziom | wzorzec | połowa uczenia | połowa testu | powtarza się |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for d in sh["details"]:
        L.append(f"| {d['pid']} | {d['dir']} | {d['kind']} | {d['level']} | {d['pattern']} | {d['train']} | "
                 f"{d['test']} | {'tak' if d['replicates'] else 'nie'} |")
    wk = r["weekday_check"]
    L += ["", "## Kontrola weekendu (istotne wzorce, tylko dni z D-1 w dzień roboczy)", "",
          f"Trzyma się: {sum(d['holds'] for d in wk)}/{len(wk)}.", "",
          "| osoba | rodzaj | wzorzec | wszystkie dni | dni robocze | trzyma się |", "| --- | --- | --- | --- | --- | --- |"]
    for d in wk:
        L.append(f"| {d['pid']} | {d['kind']} | {d['pattern']} | {d['all_days']} | {d['weekdays']} | "
                 f"{'tak' if d['holds'] else 'nie'} |")
    inj = r["injected"]
    L += ["", "## Wstrzyknięty efekt", "",
          f"Reguła „sen < 6 h → zły dzień z p=0,7 (inaczej 0,2)” na prawdziwych cechach, {inj['runs']} przebiegów: "
          f"silnik znajduje istotny wzorzec snu w {inj['found_rate']:.0%}, z progiem w odległości ≤ 0,5 h od 6 h "
          f"w {inj['threshold_within_0.5h_rate']:.0%}."]
    (OUT / "validation.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:12]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=100)
    main(ap.parse_args().runs)
