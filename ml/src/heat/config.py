"""Configuration and constants for the heat ML pipeline."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_ROOT = ML_ROOT / "artifacts" / "heat"
DEFAULT_RANDOM_STATE = 42

# USGS Landsat Collection 2 Level 2 surface temperature scaling.
ST_B10_SCALE = 0.00341802
ST_B10_OFFSET_KELVIN = 149.0
KELVIN_TO_CELSIUS = 273.15

# Collection 2 Level 2 surface-reflectance scaling.
SR_SCALE = 0.0000275
SR_OFFSET = -0.2

TARGET_COLUMN = "lst_c"
REQUIRED_COLUMNS = (
    "cell_code",
    "observed_on",
    "scene_id",
    TARGET_COLUMN,
    "ndvi",
    "ndbi",
    "mndwi",
    "valid_pixel_fraction",
    "cloud_cover_pct",
    "centroid_lat",
    "centroid_lon",
    "elevation_m",
)

FEATURE_COLUMNS = (
    "ndvi",
    "ndbi",
    "mndwi",
    "elevation_m",
    "cloud_cover_pct",
    "valid_pixel_fraction",
    "centroid_lat",
    "centroid_lon",
    "day_of_year_sin",
    "day_of_year_cos",
    "year_offset",
)

MIN_ROWS = 500
MIN_DATES = 20
MIN_TEST_DATES = 10
MIN_VALID_PIXEL_FRACTION = 0.5
DEFAULT_TEST_FRACTION = 0.2

KOLKATA_BBOX = {
    "min_lon": 88.20,
    "min_lat": 22.40,
    "max_lon": 88.55,
    "max_lat": 22.75,
}


def utc_today() -> date:
    from datetime import UTC, datetime

    return datetime.now(UTC).date()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ML_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    commit = result.stdout.strip()
    return commit or None


def library_versions() -> dict:
    versions = {"python": platform.python_version()}
    for name in ("numpy", "pandas", "sklearn", "xgboost", "joblib"):
        try:
            module = __import__(name)
        except ImportError:
            versions[name] = None
            continue
        versions[name] = getattr(module, "__version__", None)
    return versions


def run_id(prefix: str = "lst") -> str:
    from datetime import UTC, datetime

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{stamp}"


@dataclass
class TrainingConfig:
    dataset: str
    test_fraction: float = DEFAULT_TEST_FRACTION
    random_state: int = DEFAULT_RANDOM_STATE
    min_rows: int = MIN_ROWS
    min_dates: int = MIN_DATES
    min_test_dates: int = MIN_TEST_DATES
    min_valid_pixel_fraction: float = MIN_VALID_PIXEL_FRACTION
    target: str = TARGET_COLUMN
    features: tuple[str, ...] = FEATURE_COLUMNS
    model: dict = field(
        default_factory=lambda: {
            "n_estimators": 400,
            "max_depth": 4,
            "learning_rate": 0.05,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "objective": "reg:squarederror",
            "tree_method": "hist",
        }
    )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DatasetSummary:
    path: str
    sha256: str
    rows: int
    dropped_rows: int
    dates: list[str]
    cell_count: int
    start_date: str
    end_date: str


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)
        handle.write("\n")


def env_or_none(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def require_reason(*names: str) -> str | None:
    missing = [name for name in names if not env_or_none(name)]
    if missing:
        return "Missing required environment variables: " + ", ".join(missing)
    return None


def fail(message: str, code: int = 2) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)
