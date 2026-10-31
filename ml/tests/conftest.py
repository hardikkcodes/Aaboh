from __future__ import annotations

import math
from datetime import date, timedelta

import pandas as pd
import pytest


def build_frame(
    *,
    rows: int = 600,
    dates: int = 60,
    cells: int = 20,
    start: date = date(2024, 1, 1),
) -> pd.DataFrame:
    records = []
    for index in range(rows):
        day = start + timedelta(days=index % dates)
        cell_index = index % cells
        ndvi = round(0.15 + 0.02 * (cell_index % 5), 3)
        ndbi = round(0.35 - 0.01 * (cell_index % 4), 3)
        mndwi = round(-0.2 + 0.005 * (cell_index % 3), 3)
        seasonal = 6.0 * math.sin(2 * math.pi * day.timetuple().tm_yday / 365.25)
        target = 32.0 + seasonal + 8.0 * ndbi - 6.0 * ndvi + 0.001 * (index % 7)
        records.append(
            {
                "cell_code": f"KOL-{cell_index + 1:03d}",
                "observed_on": day.isoformat(),
                "scene_id": f"LC09_{day.strftime('%Y%m%d')}",
                "lst_c": round(target, 3),
                "ndvi": ndvi,
                "ndbi": ndbi,
                "mndwi": mndwi,
                "valid_pixel_fraction": 0.9,
                "cloud_cover_pct": 8.0,
                "centroid_lat": 22.55,
                "centroid_lon": 88.35,
                "elevation_m": 6.0,
            }
        )
    return pd.DataFrame.from_records(records)


@pytest.fixture
def dataset_csv(tmp_path):
    frame = build_frame()
    path = tmp_path / "observations.csv"
    frame.to_csv(path, index=False)
    return path
