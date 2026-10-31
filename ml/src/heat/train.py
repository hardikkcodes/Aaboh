"""Train an evaluated land-surface temperature regressor.

The script refuses to run without a real observation dataset. It never writes
placeholder metrics.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .config import (
    ARTIFACT_ROOT,
    TARGET_COLUMN,
    TrainingConfig,
    fail,
    git_commit,
    library_versions,
    run_id,
    utc_today,
    write_json,
)
from .features import DatasetError, PreparedDataset, prepare_dataset


@dataclass
class TrainedModel:
    estimator: object
    metrics: dict
    feature_columns: list[str]


def _require_xgboost():
    try:
        from xgboost import XGBRegressor
    except ImportError as exc:  # pragma: no cover - exercised only without extras
        raise RuntimeError(
            "xgboost is not installed. Install ML dependencies with "
            "`pip install -r ml/requirements.txt`."
        ) from exc
    return XGBRegressor


def train_model(prepared: PreparedDataset, config: TrainingConfig) -> TrainedModel:
    XGBRegressor = _require_xgboost()
    features = prepared.feature_columns
    if not features:
        raise DatasetError("No usable feature columns were found.")

    estimator = XGBRegressor(
        random_state=config.random_state,
        n_jobs=4,
        **config.model,
    )
    estimator.fit(
        prepared.train[features],
        prepared.train[TARGET_COLUMN],
        eval_set=[(prepared.test[features], prepared.test[TARGET_COLUMN])],
        verbose=False,
    )

    predictions = estimator.predict(prepared.test[features])
    actual = prepared.test[TARGET_COLUMN].to_numpy()
    # Baseline: each cell's past average for that month. A useful model has to beat
    # simply knowing the place and the season.
    history = prepared.train.assign(month=prepared.train["observed_on"].dt.month)
    usual = history.groupby(["cell_code", "month"])[TARGET_COLUMN].mean()
    monthly = history.groupby("month")[TARGET_COLUMN].mean()
    lookup = pd.MultiIndex.from_arrays([prepared.test["cell_code"], prepared.test["observed_on"].dt.month])
    baseline = (
        pd.Series(usual.reindex(lookup).to_numpy(), index=prepared.test.index)
        .fillna(prepared.test["observed_on"].dt.month.map(monthly))
        .fillna(prepared.train[TARGET_COLUMN].mean())
    )
    metrics = {
        "target": TARGET_COLUMN,
        "unit": "degrees_celsius",
        "split": "chronological_holdout",
        "test_start": str(prepared.cutoff.date()),
        "n_train_rows": int(len(prepared.train)),
        "n_test_rows": int(len(prepared.test)),
        "n_train_dates": int(prepared.train["observed_on"].dt.normalize().nunique()),
        "n_test_dates": int(prepared.test["observed_on"].dt.normalize().nunique()),
        "mae_c": round(float(mean_absolute_error(actual, predictions)), 4),
        "rmse_c": round(float(np.sqrt(mean_squared_error(actual, predictions))), 4),
        "r2": round(float(r2_score(actual, predictions)), 4),
        "mean_error_c": round(float(np.mean(predictions - actual)), 4),
        "baseline_cell_month_mae_c": round(float(mean_absolute_error(actual, baseline)), 4),
        "note": (
            "Metrics describe the held-out chronological period only. They are not an "
            "official accuracy claim and do not imply air-temperature accuracy."
        ),
    }
    return TrainedModel(estimator=estimator, metrics=metrics, feature_columns=features)


def write_artifact(
    prepared: PreparedDataset,
    trained: TrainedModel,
    config: TrainingConfig,
    output_root: Path = ARTIFACT_ROOT,
    run_name: str | None = None,
) -> Path:
    identifier = run_name or run_id()
    target = output_root / identifier
    target.mkdir(parents=True, exist_ok=False)

    bundle = {
        "model": trained.estimator,
        "feature_columns": trained.feature_columns,
        "target": TARGET_COLUMN,
        "config": config.to_dict(),
        "trained_at": utc_today().isoformat(),
    }
    joblib.dump(bundle, target / "model.joblib")

    write_json(target / "metrics.json", trained.metrics)
    manifest = {
        "run_id": identifier,
        "created_at": utc_today().isoformat(),
        "dataset": prepared.summary.__dict__,
        "config": config.to_dict(),
        "feature_columns": trained.feature_columns,
        "split_cutoff": str(prepared.cutoff.date()),
        "libraries": library_versions(),
        "git_commit": git_commit(),
        "target": TARGET_COLUMN,
        "target_unit": "degrees_celsius",
        "artifact": "model.joblib",
        "limitations": [
            "Land-surface temperature is not air temperature.",
            "Landsat revisit and cloud cover limit temporal coverage.",
            "The 1 km grid is an aggregation unit, not the native thermal resolution.",
            "Metrics cover a single chronological hold-out and are not a guarantee.",
        ],
    }
    write_json(target / "manifest.json", manifest)
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train the LST regressor on exported Landsat observations.")
    parser.add_argument("--dataset", required=True, help="CSV/JSON/Parquet observation dataset")
    parser.add_argument("--test-fraction", type=float, default=TrainingConfig(dataset="").test_fraction)
    parser.add_argument("--random-state", type=int, default=TrainingConfig(dataset="").random_state)
    parser.add_argument("--output-root", default=str(ARTIFACT_ROOT))
    parser.add_argument("--run-name", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = TrainingConfig(
        dataset=args.dataset,
        test_fraction=args.test_fraction,
        random_state=args.random_state,
    )
    try:
        prepared = prepare_dataset(args.dataset, config)
    except DatasetError as exc:
        fail(str(exc))
    trained = train_model(prepared, config)
    target = write_artifact(prepared, trained, config, Path(args.output_root), args.run_name)
    print(f"trained {len(trained.feature_columns)} features on {prepared.summary.rows} rows")
    print(f"held-out metrics: {trained.metrics['mae_c']} °C MAE, {trained.metrics['rmse_c']} °C RMSE")
    print(f"artifact: {target}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
