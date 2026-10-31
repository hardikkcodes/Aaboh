"""Dataset validation, feature engineering and chronological splitting."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from .config import (
    FEATURE_COLUMNS,
    REQUIRED_COLUMNS,
    TARGET_COLUMN,
    DatasetSummary,
    TrainingConfig,
    sha256_file,
)


class DatasetError(ValueError):
    """Raised when an observation dataset cannot be used for training."""


@dataclass
class PreparedDataset:
    frame: pd.DataFrame
    train: pd.DataFrame
    test: pd.DataFrame
    cutoff: pd.Timestamp
    summary: DatasetSummary

    @property
    def feature_columns(self) -> list[str]:
        return [column for column in FEATURE_COLUMNS if column in self.frame.columns]


def read_dataset(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if not source.exists():
        raise DatasetError(
            f"Dataset not found: {source}. Export observations with "
            "`python -m src.heat.gee_landsat_export` before training."
        )
    suffix = source.suffix.lower()
    if suffix in {".csv", ".txt"}:
        frame = pd.read_csv(source)
    elif suffix in {".json", ".geojson"}:
        frame = pd.read_json(source)
    elif suffix == ".parquet":
        frame = pd.read_parquet(source)
    else:
        raise DatasetError(f"Unsupported dataset format: {suffix}. Use CSV, JSON, GeoJSON or Parquet.")
    if frame.empty:
        raise DatasetError(f"Dataset is empty: {source}")
    return frame


def validate_columns(frame: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise DatasetError(
            "Dataset is missing required columns: " + ", ".join(missing) + ". "
            "See ml/README.md for the export contract."
        )


def _clean(frame: pd.DataFrame, min_valid_pixel_fraction: float) -> tuple[pd.DataFrame, int]:
    working = frame.copy()
    originating_rows = len(working)

    working["observed_on"] = pd.to_datetime(working["observed_on"], errors="coerce")
    working[TARGET_COLUMN] = pd.to_numeric(working[TARGET_COLUMN], errors="coerce")
    for column in (
        "ndvi",
        "ndbi",
        "mndwi",
        "valid_pixel_fraction",
        "cloud_cover_pct",
        "centroid_lat",
        "centroid_lon",
        "elevation_m",
    ):
        working[column] = pd.to_numeric(working[column], errors="coerce")

    working = working.dropna(subset=["observed_on", TARGET_COLUMN, "cell_code", "scene_id"])
    working = working[working["valid_pixel_fraction"] >= min_valid_pixel_fraction]

    # Physical range guards. Values outside these bounds almost always indicate a
    # scaling bug in the export, so they are rejected instead of clipped.
    working = working[working[TARGET_COLUMN].between(-30, 80)]
    working = working[working["ndvi"].between(-1, 1, inclusive="both")]
    working = working[working["ndbi"].between(-1, 1, inclusive="both")]
    working = working[working["mndwi"].between(-1, 1, inclusive="both")]
    working = working[working["centroid_lat"].between(-90, 90)]
    working = working[working["centroid_lon"].between(-180, 180)]

    working["cell_code"] = working["cell_code"].astype(str)
    working["scene_id"] = working["scene_id"].astype(str)
    working = working.sort_values(["observed_on", "cell_code"]).reset_index(drop=True)
    return working, originating_rows - len(working)


def add_time_features(frame: pd.DataFrame) -> pd.DataFrame:
    working = frame.copy()
    day = working["observed_on"].dt.strftime("%j").astype(float)
    working["day_of_year_sin"] = np.sin(2 * math.pi * day / 365.25)
    working["day_of_year_cos"] = np.cos(2 * math.pi * day / 365.25)
    working["year_offset"] = working["observed_on"].dt.year - 2013
    return working


def prepare_dataset(
    path: str | Path,
    config: TrainingConfig | None = None,
) -> PreparedDataset:
    config = config or TrainingConfig(dataset=str(path))
    frame = read_dataset(path)
    validate_columns(frame)
    cleaned, dropped = _clean(frame, config.min_valid_pixel_fraction)
    if cleaned.empty:
        raise DatasetError(
            "No valid observations remain after quality filtering. Check the export and "
            f"valid_pixel_fraction >= {config.min_valid_pixel_fraction}."
        )
    if len(cleaned) < config.min_rows:
        raise DatasetError(
            f"Dataset has {len(cleaned)} valid rows; at least {config.min_rows} are required "
            "before a model may be trained."
        )

    unique_dates = sorted(cleaned["observed_on"].dt.normalize().unique())
    if len(unique_dates) < config.min_dates:
        raise DatasetError(
            f"Dataset covers {len(unique_dates)} observation dates; at least {config.min_dates} "
            "are required to make a chronological split meaningful."
        )

    prepared = add_time_features(cleaned)
    feature_columns = [column for column in FEATURE_COLUMNS if column in prepared.columns]
    usable = prepared.dropna(subset=[*feature_columns, TARGET_COLUMN]).reset_index(drop=True)
    dropped += len(prepared) - len(usable)

    dates = pd.Series(sorted(usable["observed_on"].dt.normalize().unique()))
    split_index = max(1, int(math.floor(len(dates) * (1 - config.test_fraction))))
    split_index = min(split_index, len(dates) - 1)
    cutoff = pd.Timestamp(dates.iloc[split_index])

    train = usable[usable["observed_on"] < cutoff].reset_index(drop=True)
    test = usable[usable["observed_on"] >= cutoff].reset_index(drop=True)
    test_dates = test["observed_on"].dt.normalize().nunique()
    if test_dates < config.min_test_dates:
        raise DatasetError(
            f"Held-out period has {test_dates} observation dates; at least "
            f"{config.min_test_dates} are required."
        )
    if test.empty or train.empty:
        raise DatasetError("Chronological split produced an empty train or test partition.")

    summary = DatasetSummary(
        path=str(Path(path).resolve()),
        sha256=sha256_file(Path(path)),
        rows=len(usable),
        dropped_rows=dropped,
        dates=[pd.Timestamp(value).date().isoformat() for value in dates],
        cell_count=int(usable["cell_code"].nunique()),
        start_date=usable["observed_on"].min().date().isoformat(),
        end_date=usable["observed_on"].max().date().isoformat(),
    )
    return PreparedDataset(
        frame=usable,
        train=train,
        test=test,
        cutoff=cutoff,
        summary=summary,
    )


def prediction_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Validate an unlabelled feature frame for prediction.

    The target is optional. Rows missing features are rejected rather than
    imputed, because silent imputation would hide export problems.
    """
    missing = [column for column in REQUIRED_COLUMNS if column not in frame.columns]
    target_missing = TARGET_COLUMN in missing
    if target_missing:
        missing.remove(TARGET_COLUMN)
    if missing:
        raise DatasetError("Prediction input is missing columns: " + ", ".join(missing))

    working = frame.copy()
    working["observed_on"] = pd.to_datetime(working["observed_on"], errors="coerce")
    if working["observed_on"].isna().any():
        raise DatasetError("Prediction input contains invalid observed_on values.")
    working = add_time_features(working)
    missing_features = [column for column in FEATURE_COLUMNS if column not in working.columns]
    if missing_features:
        raise DatasetError("Prediction input is missing features: " + ", ".join(missing_features))
    if working[list(FEATURE_COLUMNS)].isna().any().any():
        raise DatasetError("Prediction input contains missing feature values; refusing to impute.")
    return working
