"""Train next-day heat and heavy-rain models, and judge them against the raw forecast.

A model that doesn't beat the forecast it was built from has no reason to exist, so each
one must clear a baseline on a later, unseen period before it is marked as promotable.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, mean_absolute_error, precision_score, recall_score
from xgboost import XGBClassifier, XGBRegressor

from ..heat.config import ML_ROOT, git_commit, library_versions, run_id, sha256_file, write_json
from .dataset import DEFAULT_OUTPUT

ARTIFACT_ROOT = ML_ROOT / "artifacts" / "forecast"
TEST_FRACTION = 0.3
HEAVY_RAIN_MM = 20.0
MIN_IMPROVEMENT = 0.05
FEATURES = [
    "forecast_tmax",
    "forecast_tmin",
    "forecast_rh",
    "forecast_rain",
    "forecast_peak_rain",
    "forecast_cloud",
    "forecast_wind",
    "forecast_rain_prev_3d",
    "day_sin",
    "day_cos",
]
PARAMS = {"n_estimators": 200, "max_depth": 3, "learning_rate": 0.03, "subsample": 0.8, "random_state": 42}


def chronological_split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cutoff = int(len(frame) * (1 - TEST_FRACTION))
    return frame.iloc[:cutoff], frame.iloc[cutoff:]


def train_heat(train: pd.DataFrame, test: pd.DataFrame) -> tuple[object, dict]:
    """Predict the forecast's error, so the model can only adjust what the forecast already says."""
    model = XGBRegressor(**PARAMS)
    model.fit(train[FEATURES], train["actual_tmax"] - train["forecast_tmax"])
    corrected = test["forecast_tmax"] + model.predict(test[FEATURES])
    model_mae = float(mean_absolute_error(test["actual_tmax"], corrected))
    baseline_mae = float(mean_absolute_error(test["actual_tmax"], test["forecast_tmax"]))
    # A fixed offset is the tougher baseline: it copies any average gap between the two datasets.
    mean_gap = float((train["actual_tmax"] - train["forecast_tmax"]).mean())
    offset_mae = float(mean_absolute_error(test["actual_tmax"], test["forecast_tmax"] + mean_gap))
    improvement = (offset_mae - model_mae) / offset_mae
    return model, {
        "target": "next_day_max_temperature_c",
        "metric": "mean_absolute_error_c",
        "model": round(model_mae, 3),
        "baseline_raw_forecast": round(baseline_mae, 3),
        "baseline_fixed_offset": round(offset_mae, 3),
        "mean_forecast_minus_target_c": round(-mean_gap, 3),
        "improvement_over_raw_pct": round((baseline_mae - model_mae) / baseline_mae * 100, 1),
        "improvement_pct": round(improvement * 100, 1),
        "promotable": improvement >= MIN_IMPROVEMENT,
    }


def train_rain(train: pd.DataFrame, test: pd.DataFrame) -> tuple[dict, dict]:
    labels_train = (train["actual_rain"] >= HEAVY_RAIN_MM).astype(int)
    labels_test = (test["actual_rain"] >= HEAVY_RAIN_MM).astype(int)

    # The last part of training calibrates probabilities without touching the test period.
    fit_end = int(len(train) * 0.75)
    model = XGBClassifier(**PARAMS, eval_metric="logloss")
    model.fit(train[FEATURES].iloc[:fit_end], labels_train.iloc[:fit_end])
    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1)
    calibrator.fit(model.predict_proba(train[FEATURES].iloc[fit_end:])[:, 1], labels_train.iloc[fit_end:])
    probability = calibrator.predict(model.predict_proba(test[FEATURES])[:, 1])

    # Fair baseline: the chance of heavy rain seen in training at each raw forecast level.
    bands = [-1, 1, 5, 10, 20, 40, 1e6]
    band_train = pd.cut(train["forecast_rain"], bands)
    rates = labels_train.groupby(band_train, observed=False).mean().fillna(labels_train.mean())
    baseline = pd.cut(test["forecast_rain"], bands).map(rates).astype(float).to_numpy()

    model_brier = float(brier_score_loss(labels_test, probability))
    baseline_brier = float(brier_score_loss(labels_test, baseline))
    climatology = float(brier_score_loss(labels_test, np.full(len(labels_test), labels_train.mean())))
    improvement = (baseline_brier - model_brier) / baseline_brier
    warned = probability >= 0.3
    raw_warned = test["forecast_rain"] >= HEAVY_RAIN_MM
    return {"model": model, "calibrator": calibrator}, {
        "target": f"next_day_rain_at_least_{HEAVY_RAIN_MM:g}_mm",
        "metric": "brier_score_lower_is_better",
        "model": round(model_brier, 4),
        "baseline_calibrated_forecast": round(baseline_brier, 4),
        "baseline_climatology": round(climatology, 4),
        "improvement_pct": round(improvement * 100, 1),
        "heavy_days_in_test": int(labels_test.sum()),
        "model_recall_at_30pct": round(float(recall_score(labels_test, warned, zero_division=0)), 3),
        "model_precision_at_30pct": round(float(precision_score(labels_test, warned, zero_division=0)), 3),
        "raw_forecast_recall_at_20mm": round(float(recall_score(labels_test, raw_warned, zero_division=0)), 3),
        "raw_forecast_precision_at_20mm": round(float(precision_score(labels_test, raw_warned, zero_division=0)), 3),
        "promotable": improvement >= MIN_IMPROVEMENT and int(labels_test.sum()) >= 20,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train next-day models on real forecast history.")
    parser.add_argument("--dataset", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--output-root", default=str(ARTIFACT_ROOT))
    args = parser.parse_args(argv)

    dataset = Path(args.dataset)
    frame = pd.read_csv(dataset, parse_dates=["date"])
    train, test = chronological_split(frame)
    heat_model, heat_metrics = train_heat(train, test)
    rain_bundle, rain_metrics = train_rain(train, test)

    target = Path(args.output_root) / run_id("next-day")
    target.mkdir(parents=True, exist_ok=False)
    joblib.dump({"heat": heat_model, **rain_bundle, "features": FEATURES}, target / "model.joblib")
    report = {
        "dataset": {
            "path": dataset.name,
            "sha256": sha256_file(dataset),
            "rows": len(frame),
            "train_period": [str(train["date"].min().date()), str(train["date"].max().date())],
            "test_period": [str(test["date"].min().date()), str(test["date"].max().date())],
        },
        "features": FEATURES,
        "heat": heat_metrics,
        "rain": rain_metrics,
        "limitations": [
            "Targets are ERA5 reanalysis (about 25 km), not gauges or stations.",
            "ERA5 smooths local storms, so heavy-rain labels miss some real events.",
            "One point for the whole city; this says nothing about individual streets.",
            "This does not predict waterlogging.",
        ],
        "libraries": library_versions(),
        "git_commit": git_commit(),
    }
    write_json(target / "metrics.json", report)
    print(f"train {report['dataset']['train_period']}  test {report['dataset']['test_period']}")
    print("heat", heat_metrics)
    print("rain", rain_metrics)
    print(f"artifact: {target}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
