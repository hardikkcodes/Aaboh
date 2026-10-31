from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from src.waterlogging.terrain_export import fill_depressions, flow_accumulation, score
from src.waterlogging.train import MIN_FLOODED_ROWS, TERRAIN_FEATURES, NotEnoughLabels, train


def _rows(flooded_rows: int, dates: int = 40) -> pd.DataFrame:
    """A small synthetic table, used only to test the training rules."""
    random = np.random.default_rng(1)
    size = max(flooded_rows * 4, dates * 4)
    frame = pd.DataFrame({name: random.normal(size=size) for name in TERRAIN_FEATURES})
    frame["date"] = [f"2030-{(i % dates) // 28 + 1:02d}-{(i % dates) % 28 + 1:02d}" for i in range(size)]
    frame["rain_1d_mm"] = random.uniform(10, 120, size)
    frame["rain_3d_mm"] = frame["rain_1d_mm"] + random.uniform(0, 50, size)
    risk = frame["rain_1d_mm"] / 120 - frame["elevation_m"]
    frame["flooded"] = 0
    frame.loc[risk.nlargest(flooded_rows).index, "flooded"] = 1
    return frame


def test_training_refuses_too_few_real_reports():
    with pytest.raises(NotEnoughLabels):
        train(_rows(MIN_FLOODED_ROWS - 1))


def test_terrain_signal_beats_rain_alone():
    metrics = train(_rows(MIN_FLOODED_ROWS))["metrics"]
    assert metrics["beats_baseline"]


def test_a_hollow_is_filled_to_its_spill_level():
    dem = np.full((5, 5), 10.0)
    dem[2, 2] = 7.0
    assert fill_depressions(dem)[2, 2] == pytest.approx(10.0, abs=0.01)


def test_water_gathers_downhill():
    dem = np.tile(np.arange(6, 0, -1, dtype=float), (3, 1))
    accumulation = flow_accumulation(fill_depressions(dem))
    assert accumulation[1, -1] > accumulation[1, 0]


def test_low_hollow_cells_score_highest():
    frame = pd.DataFrame(
        {
            "relative_elevation_m": [-3.0, 0.0, 3.0, 1.0],
            "depression_fraction": [0.4, 0.1, 0.0, 0.0],
            "twi": [12.0, 9.0, 7.0, 8.0],
            "built_up_index": [0.1, 0.0, -0.2, -0.1],
        }
    )
    assert score(frame).iloc[0]["terrain_class"] == "high"
