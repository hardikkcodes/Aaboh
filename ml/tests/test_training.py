from __future__ import annotations

import json

from src.heat.config import TrainingConfig
from src.heat.features import prepare_dataset
from src.heat.predict import predict
from src.heat.train import train_model, write_artifact


def test_training_writes_reproducible_artifacts(dataset_csv, tmp_path):
    config = TrainingConfig(dataset=str(dataset_csv))
    prepared = prepare_dataset(dataset_csv, config)
    trained = train_model(prepared, config)

    artifact = write_artifact(prepared, trained, config, output_root=tmp_path, run_name="test-run")
    assert (artifact / "model.joblib").exists()
    assert (artifact / "metrics.json").exists()
    manifest = json.loads((artifact / "manifest.json").read_text(encoding="utf-8"))
    metrics = json.loads((artifact / "metrics.json").read_text(encoding="utf-8"))

    assert manifest["run_id"] == "test-run"
    assert manifest["dataset"]["rows"] == prepared.summary.rows
    assert manifest["feature_columns"] == trained.feature_columns
    assert metrics["n_test_rows"] == len(prepared.test)
    assert "not an official accuracy claim" in metrics["note"]
    assert metrics["mae_c"] >= 0

    # Predictions are produced from the same artefact and remain labelled as LST.
    predictions = predict(artifact, str(dataset_csv))
    assert len(predictions) == len(prepared.frame)
    assert "predicted_lst_c" in predictions.columns
    assert "not measured air temperature" in predictions["disclaimer"].iloc[0]
