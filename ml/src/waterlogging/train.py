"""Train the waterlogging model from real reports, terrain and historical rain.

Each row is one grid cell on one wet day, from ``manage.py export_waterlogging_dataset``.
``flooded`` is 1 when residents reported water in that cell that day. A cell with no
report may still have flooded, so the score is relative, not a true probability.

Training refuses to run on too few real reports, and a model is only kept if it beats
rain alone on later dates.

Example
-------
    python -m src.waterlogging.train --dataset data/raw/waterlogging.csv
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score

MIN_FLOODED_ROWS = 300
MIN_WET_DATES = 30
TEST_FRACTION = 0.25
RAIN_FEATURES = ["rain_1d_mm", "rain_3d_mm"]
TERRAIN_FEATURES = [
    "elevation_m",
    "relative_elevation_m",
    "slope_deg",
    "twi",
    "depression_fraction",
    "built_up_index",
]
LABEL = "flooded"
ARTIFACT_ROOT = Path(__file__).resolve().parents[2] / "artifacts" / "waterlogging"


class NotEnoughLabels(Exception):
    pass


def split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Later dates are the test, so the model can't learn from a storm it is tested on."""
    missing = {LABEL, "date", *RAIN_FEATURES, *TERRAIN_FEATURES}.difference(frame.columns)
    if missing:
        raise NotEnoughLabels("Dataset is missing columns: " + ", ".join(sorted(missing)))
    flooded = int(frame[LABEL].sum())
    dates = sorted(frame["date"].unique())
    if flooded < MIN_FLOODED_ROWS:
        raise NotEnoughLabels(f"{flooded} real flooded rows; at least {MIN_FLOODED_ROWS} are needed.")
    if len(dates) < MIN_WET_DATES:
        raise NotEnoughLabels(f"{len(dates)} wet dates; at least {MIN_WET_DATES} are needed.")
    cutoff = dates[int(len(dates) * (1 - TEST_FRACTION))]
    return frame[frame["date"] < cutoff], frame[frame["date"] >= cutoff]


def train(frame: pd.DataFrame, *, random_state: int = 42) -> dict:
    train_rows, test_rows = split(frame)
    if not test_rows[LABEL].sum():
        raise NotEnoughLabels("The test dates hold no flooded rows.")
    features = RAIN_FEATURES + TERRAIN_FEATURES
    baseline = LogisticRegression(class_weight="balanced", max_iter=1000)
    baseline.fit(train_rows[RAIN_FEATURES], train_rows[LABEL])
    model = HistGradientBoostingClassifier(class_weight="balanced", max_depth=4, random_state=random_state)
    model.fit(train_rows[features], train_rows[LABEL])

    actual = test_rows[LABEL]
    model_score = average_precision_score(actual, model.predict_proba(test_rows[features])[:, 1])
    baseline_score = average_precision_score(actual, baseline.predict_proba(test_rows[RAIN_FEATURES])[:, 1])
    return {
        "model": model,
        "features": features,
        "metrics": {
            "average_precision": round(float(model_score), 4),
            "baseline_rain_only": round(float(baseline_score), 4),
            "base_rate": round(float(actual.mean()), 4),
            "flooded_rows": int(frame[LABEL].sum()),
            "train_dates": int(train_rows["date"].nunique()),
            "test_dates": int(test_rows["date"].nunique()),
            "beats_baseline": bool(model_score > baseline_score),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    args = parser.parse_args(argv)
    try:
        result = train(pd.read_csv(args.dataset))
    except NotEnoughLabels as exc:
        print(f"Not training: {exc}")
        return 1
    print(result["metrics"])
    if not result["metrics"]["beats_baseline"]:
        print("Not saved: terrain did not beat rain alone.")
        return 1
    target = ARTIFACT_ROOT / datetime.now(UTC).strftime("wl-%Y%m%dT%H%M%SZ")
    target.mkdir(parents=True)
    joblib.dump({"model": result["model"], "features": result["features"]}, target / "model.joblib")
    (target / "metrics.json").write_text(pd.Series(result["metrics"]).to_json(indent=2), encoding="utf-8")
    print(f"artifact: {target}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
