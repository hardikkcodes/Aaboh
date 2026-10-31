"""Recompute metrics for a saved artefact against a dataset.

Stored metrics are never edited. Evaluation writes a separate report so that a
later dataset cannot silently overwrite the historical record of a run.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from .config import ARTIFACT_ROOT, TARGET_COLUMN, TrainingConfig, fail, write_json
from .features import DatasetError, prepare_dataset


def evaluate_artifact(artifact_dir: Path, dataset: str) -> dict:
    model_path = artifact_dir / "model.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"No model.joblib in {artifact_dir}")
    bundle = joblib.load(model_path)
    config = TrainingConfig(**{**bundle["config"], "dataset": dataset})
    prepared = prepare_dataset(dataset, config)
    features = bundle["feature_columns"]
    missing = [column for column in features if column not in prepared.frame.columns]
    if missing:
        raise DatasetError("Dataset is missing model features: " + ", ".join(missing))

    test = prepared.frame[prepared.frame["observed_on"] >= prepared.cutoff]
    predictions = bundle["model"].predict(test[features])
    actual = test[TARGET_COLUMN].to_numpy()
    return {
        "artifact": str(artifact_dir),
        "dataset": str(Path(dataset).resolve()),
        "test_start": str(prepared.cutoff.date()),
        "n_test_rows": int(len(test)),
        "mae_c": round(float(mean_absolute_error(actual, predictions)), 4),
        "rmse_c": round(float(np.sqrt(mean_squared_error(actual, predictions))), 4),
        "r2": round(float(r2_score(actual, predictions)), 4),
        "note": "Independent recomputation; stored metrics.json is unchanged.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate a saved LST artefact.")
    parser.add_argument("--artifact", required=True, help="Artifact directory or run id")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)

    artifact = Path(args.artifact)
    if not artifact.exists() and (ARTIFACT_ROOT / args.artifact).exists():
        artifact = ARTIFACT_ROOT / args.artifact
    try:
        report = evaluate_artifact(artifact, args.dataset)
    except (DatasetError, FileNotFoundError) as exc:
        fail(str(exc))
    output = Path(args.output) if args.output else artifact / "evaluation.json"
    write_json(output, report)
    print(json.dumps(report, indent=2))
    print(f"report: {output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
