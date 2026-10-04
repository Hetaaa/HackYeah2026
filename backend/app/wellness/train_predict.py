import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from app.wellness.build_features import FEATURES


def predict(train: pd.DataFrame, test: pd.DataFrame, target_user: str) -> np.ndarray:
    if train.empty:
        raise ValueError("No historical labeled days available")
    y = train.label.to_numpy(dtype=int)
    weights = compute_sample_weight("balanced", y) * np.where(train.pid == target_user, 3.0, 1.0)
    # XGBoost requires contiguous observed classes; map absent classes back to zero probability.
    classes, encoded = np.unique(y, return_inverse=True)
    result = np.zeros((len(test), 3))
    if len(classes) == 1:
        result[:, classes[0]] = 1
        return result
    imputer = SimpleImputer(strategy="median", keep_empty_features=True)
    x_train = imputer.fit_transform(train[FEATURES])
    x_test = imputer.transform(test[FEATURES])
    for seed in (0, 1, 2):
        model = XGBClassifier(
            n_estimators=120,
            max_depth=2,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.7,
            min_child_weight=3,
            reg_lambda=5,
            random_state=seed,
            n_jobs=1,
            eval_metric="mlogloss",
        )
        model.fit(x_train, encoded, sample_weight=weights)
        result[:, classes] += model.predict_proba(x_test) / 3
    return result


def blocks(features: pd.DataFrame):
    for pid, user in features.groupby("pid", sort=True):
        user = user.sort_values("date")
        edges = [int(len(user) * f) for f in (0.5, 0.625, 0.75, 0.875, 1.0)]
        for start, end in zip(edges[:-1], edges[1:], strict=True):
            test = user.iloc[start:end]
            if test.empty:
                continue
            cut_date = test.date.min()
            train = features[features.date < cut_date]
            yield pid, cut_date, train, test


def walk_forward(features: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for pid, cut_date, train, test in blocks(features):
        probabilities = predict(train, test, pid)
        out = test[["pid", "date"]].copy()
        out[["p_bad", "p_neutral", "p_good"]] = probabilities
        out["pred"] = probabilities.argmax(axis=1)
        out["true_label"] = test.label.astype(int)
        out["yesterday"] = test.label_y.fillna(1).astype(int)
        out["majority"] = int(train.label.value_counts().sort_index().idxmax())
        out["cut_date"] = cut_date
        parts.append(out)
    if not parts:
        raise ValueError("No walk-forward test days")
    return pd.concat(parts, ignore_index=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("predictions.csv"))
    args = parser.parse_args()
    features = pd.read_csv(args.input, parse_dates=["date"])
    walk_forward(features).to_csv(args.output, index=False)


if __name__ == "__main__":
    main()
