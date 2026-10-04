import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score

from app.wellness.build_features import build_features
from app.wellness.train_predict import walk_forward


def macro(y: np.ndarray, pred: np.ndarray) -> float:
    return float(f1_score(y, pred, labels=[0, 1, 2], average="macro", zero_division=0))


def evaluate(predictions: pd.DataFrame, resamples: int = 2000) -> dict:
    y = predictions.true_label.to_numpy()
    pred = predictions.pred.to_numpy()
    per_user = {
        pid: macro(g.true_label.to_numpy(), g.pred.to_numpy())
        for pid, g in predictions.groupby("pid")
    }
    rng = np.random.default_rng(0)
    scores, differences = [], {c: [] for c in ("yesterday", "majority")}
    for _ in range(resamples):
        idx = rng.integers(0, len(y), len(y))
        score = macro(y[idx], pred[idx])
        scores.append(score)
        for c in differences:
            differences[c].append(score - macro(y[idx], predictions[c].to_numpy()[idx]))
    return {
        "n_test_days": len(y),
        "macro_f1": macro(y, pred),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "mean_user_macro_f1": float(np.mean(list(per_user.values()))),
        "per_user_macro_f1": per_user,
        "personas_macro_f1": {p: per_user.get(p) for p in ("p01", "p06", "p10", "p16")},
        "personas_pooled_macro_f1": macro(
            predictions.loc[
                predictions.pid.isin(["p01", "p06", "p10", "p16"]), "true_label"
            ].to_numpy(),
            predictions.loc[predictions.pid.isin(["p01", "p06", "p10", "p16"]), "pred"].to_numpy(),
        )
        if predictions.pid.isin(["p01", "p06", "p10", "p16"]).any()
        else None,
        "baselines": {
            c: {
                "macro_f1": macro(y, predictions[c].to_numpy()),
                "balanced_accuracy": float(balanced_accuracy_score(y, predictions[c])),
                "difference_ci95": np.quantile(differences[c], [0.025, 0.975]).tolist(),
            }
            for c in differences
        },
        "macro_f1_ci95": np.quantile(scores, [0.025, 0.975]).tolist(),
        "bootstrap_resamples": resamples,
        "bootstrap_seed": 0,
        "leakage_review_required": macro(y, pred) >= 0.60,
    }


def write_report(output: Path, results: dict) -> None:
    (output / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    lines = [
        "# Wellness evaluation",
        "",
        "Four chronological test blocks per user; pooled training strictly before each cutoff.",
        "Fixed seeds 0,1,2; paired test-day bootstrap (2000, seed 0).",
        "Class order: bad=0, neutral=1, good=2; macro-F1 includes all three classes.",
        "Night inputs are supplied pre-survey; calendar features are known in advance.",
        "Input labels and composites are supplied targets. The source CSV calibrates them on",
        "the full pre-lockdown window; offline results are conditional on that target definition.",
        "The API freezes historical labels/composites using each day's available survey history.",
        "",
        "| Variant | Test days | Macro-F1 (95% CI) | Balanced accuracy | Mean user F1 |",
        "| --- | ---: | --- | ---: | ---: |",
    ]
    for name, metrics in results.items():
        lo, hi = metrics["macro_f1_ci95"]
        lines.append(
            f"| {name} | {metrics['n_test_days']} | {metrics['macro_f1']:.4f} "
            f"({lo:.4f}, {hi:.4f}) | {metrics['balanced_accuracy']:.4f} | "
            f"{metrics['mean_user_macro_f1']:.4f} |"
        )
    for name, metrics in results.items():
        lines += [
            "",
            f"## {name}",
            "",
            f"Eligible sleep-after-survey rows: {metrics['sleep_after_survey_rows']}.",
        ]
        for baseline, values in metrics["baselines"].items():
            lo, hi = values["difference_ci95"]
            lines.append(
                f"- {baseline}: macro-F1 {values['macro_f1']:.4f}; "
                f"model minus baseline 95% CI [{lo:.4f}, {hi:.4f}]."
            )
        lines.append(f"- Personas pooled macro-F1: {metrics['personas_pooled_macro_f1']}.")
        for pid, score in metrics["personas_macro_f1"].items():
            lines.append(
                f"- {pid}: {score:.4f}." if score is not None else f"- {pid}: no test days."
            )
        lines.append("The day bootstrap does not account for within-user temporal dependence.")
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data/wellness"))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(args.input)
    results = {}
    for safeguard in (True, False):
        folder = args.output / ("safeguard" if safeguard else "without_safeguard")
        folder.mkdir(exist_ok=True)
        features = build_features(raw, safeguard=safeguard)
        features.to_csv(folder / "features.csv", index=False)
        predictions = walk_forward(features)
        predictions.to_csv(folder / "predictions.csv", index=False)
        results[folder.name] = evaluate(predictions)
        eligible = raw[
            raw.in_analysis_window.astype(str).str.lower().eq("true") & raw.label.notna()
        ]
        results[folder.name]["sleep_after_survey_rows"] = int(
            eligible.get("sleep_after_survey", pd.Series(dtype=bool))
            .astype(str)
            .str.lower()
            .eq("true")
            .sum()
        )
        pd.DataFrame(
            confusion_matrix(predictions.true_label, predictions.pred, labels=[0, 1, 2]),
            index=["bad", "neutral", "good"],
            columns=["bad", "neutral", "good"],
        ).to_csv(folder / "confusion_matrix.csv")
    write_report(args.output, results)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
