"""Evaluation logic only. These numbers are synthetic and say nothing about real skill."""

import numpy as np
import pandas as pd
from src.forecast.train import FEATURES, chronological_split, train_heat, train_rain


def frame(rows: int = 500) -> pd.DataFrame:
    random = np.random.default_rng(1)
    data = {feature: random.normal(size=rows) for feature in FEATURES}
    data["forecast_tmax"] = random.normal(32, 3, rows)
    data["forecast_rain"] = random.exponential(6, rows)
    result = pd.DataFrame(data)
    result["date"] = pd.date_range("2024-01-01", periods=rows)
    result["actual_tmax"] = result["forecast_tmax"] - 1 + random.normal(0, 0.5, rows)
    result["actual_rain"] = result["forecast_rain"] * random.uniform(0.5, 1.5, rows)
    return result


def test_split_keeps_time_order():
    train, test = chronological_split(frame())
    assert train["date"].max() < test["date"].min()


def test_fixed_offset_alone_is_not_promotable():
    train, test = chronological_split(frame())
    _, metrics = train_heat(train, test)
    assert metrics["improvement_over_raw_pct"] > metrics["improvement_pct"]
    assert metrics["promotable"] is False


def test_rain_needs_enough_heavy_days_to_promote():
    data = frame()
    data["actual_rain"] = 0.0
    train, test = chronological_split(data)
    data.loc[train.index[:30], "actual_rain"] = 50.0
    train, test = chronological_split(data)
    _, metrics = train_rain(train, test)
    assert metrics["heavy_days_in_test"] == 0
    assert metrics["promotable"] is False
