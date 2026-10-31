from __future__ import annotations

import pandas as pd
import pytest
from src.heat.config import FEATURE_COLUMNS, TrainingConfig
from src.heat.features import (
    DatasetError,
    prediction_frame,
    prepare_dataset,
    validate_columns,
)


def test_validate_columns_reports_missing():
    with pytest.raises(DatasetError, match="missing required columns"):
        validate_columns(pd.DataFrame({"cell_code": ["a"]}))


def test_prepare_dataset_rejects_missing_file(tmp_path):
    with pytest.raises(DatasetError, match="Dataset not found"):
        prepare_dataset(tmp_path / "absent.csv", TrainingConfig(dataset="absent"))


def test_quality_filtering_and_time_features(dataset_csv):
    prepared = prepare_dataset(dataset_csv, TrainingConfig(dataset=str(dataset_csv)))
    assert not prepared.frame.empty
    assert prepared.summary.rows == len(prepared.frame)
    for column in ("day_of_year_sin", "day_of_year_cos", "year_offset"):
        assert column in prepared.frame.columns
    assert set(FEATURE_COLUMNS).issubset(prepared.frame.columns)


def test_low_valid_fraction_rows_are_dropped(tmp_path):
    frame = pd.DataFrame(
        {
            "cell_code": ["A", "B"],
            "observed_on": ["2024-01-01", "2024-01-01"],
            "scene_id": ["s1", "s1"],
            "lst_c": [30.0, 31.0],
            "ndvi": [0.2, 0.2],
            "ndbi": [0.1, 0.1],
            "mndwi": [-0.2, -0.2],
            "valid_pixel_fraction": [0.9, 0.1],
            "cloud_cover_pct": [5, 5],
            "centroid_lat": [22.5, 22.5],
            "centroid_lon": [88.3, 88.3],
            "elevation_m": [5, 5],
        }
    )
    path = tmp_path / "low.csv"
    frame.to_csv(path, index=False)
    config = TrainingConfig(dataset=str(path))
    with pytest.raises(DatasetError, match="at least"):
        prepare_dataset(path, config)


def test_chronological_split_never_leaks_future_into_training(dataset_csv):
    config = TrainingConfig(dataset=str(dataset_csv))
    prepared = prepare_dataset(dataset_csv, config)
    assert prepared.train["observed_on"].max() < prepared.test["observed_on"].min()
    assert prepared.test["observed_on"].min() == prepared.cutoff


def test_prepare_dataset_rejects_too_few_rows(tmp_path):
    frame = pd.DataFrame(
        {
            "cell_code": ["A"] * 10,
            "observed_on": ["2024-01-01"] * 10,
            "scene_id": ["s1"] * 10,
            "lst_c": [30.0] * 10,
            "ndvi": [0.2] * 10,
            "ndbi": [0.1] * 10,
            "mndwi": [-0.2] * 10,
            "valid_pixel_fraction": [0.9] * 10,
            "cloud_cover_pct": [5] * 10,
            "centroid_lat": [22.5] * 10,
            "centroid_lon": [88.3] * 10,
            "elevation_m": [5] * 10,
        }
    )
    path = tmp_path / "small.csv"
    frame.to_csv(path, index=False)
    with pytest.raises(DatasetError, match="at least 500"):
        prepare_dataset(path, TrainingConfig(dataset=str(path)))


def test_out_of_range_values_are_rejected(dataset_csv):
    frame = pd.read_csv(dataset_csv)
    frame.loc[0, "lst_c"] = 900
    path = dataset_csv.parent / "bad.csv"
    frame.to_csv(path, index=False)
    prepared = prepare_dataset(path, TrainingConfig(dataset=str(path)))
    assert 900 not in prepared.frame["lst_c"].tolist()


def test_prediction_frame_requires_target_but_not_labels(dataset_csv):
    frame = pd.read_csv(dataset_csv).drop(columns=["lst_c"])
    ready = prediction_frame(frame)
    assert len(ready) == len(frame)


def test_prediction_frame_refuses_to_impute(dataset_csv):
    frame = pd.read_csv(dataset_csv)
    frame.loc[0, "ndvi"] = None
    with pytest.raises(DatasetError, match="missing feature values"):
        prediction_frame(frame)
