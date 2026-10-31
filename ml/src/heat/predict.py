"""Generate cell-level LST predictions from a registered artefact."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd

from .config import ARTIFACT_ROOT, fail
from .features import DatasetError, prediction_frame, read_dataset


def predict(artifact_dir: Path, dataset: str) -> pd.DataFrame:
    model_path = artifact_dir / "model.joblib"
    if not model_path.exists():
        raise FileNotFoundError(f"No model.joblib in {artifact_dir}")
    bundle = joblib.load(model_path)
    frame = prediction_frame(read_dataset(dataset))
    features = bundle["feature_columns"]
    missing = [column for column in features if column not in frame.columns]
    if missing:
        raise DatasetError("Input is missing model features: " + ", ".join(missing))

    output = frame[["cell_code", "observed_on", "scene_id"]].copy()
    output["predicted_lst_c"] = bundle["model"].predict(frame[features]).round(3)
    output["model_target"] = bundle["target"]
    output["model_artifact"] = artifact_dir.name
    output["generated_at"] = datetime.now(UTC).isoformat()
    output["disclaimer"] = (
        "Estimated land-surface temperature; not measured air temperature "
        "and not an official heat warning."
    )
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Predict LST for grid cells.")
    parser.add_argument("--artifact", required=True, help="Artifact directory or run id")
    parser.add_argument("--dataset", required=True, help="Feature dataset")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)

    artifact = Path(args.artifact)
    if not artifact.exists() and (ARTIFACT_ROOT / args.artifact).exists():
        artifact = ARTIFACT_ROOT / args.artifact
    try:
        predictions = predict(artifact, args.dataset)
    except (DatasetError, FileNotFoundError) as exc:
        fail(str(exc))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(output, index=False)
    print(f"wrote {len(predictions)} predictions to {output}")
    print("Predicted LST is not air temperature and is not an official warning.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
