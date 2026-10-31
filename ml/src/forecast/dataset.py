"""Build a real next-day dataset: what the forecast said against what happened.

Features come from Open-Meteo's archived day-ahead forecasts, so the model only sees
information that existed the evening before. Targets come from ERA5 reanalysis, which
is modelled data at roughly 25 km, not a rain gauge or weather station.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from ..heat.config import ML_ROOT

PREVIOUS_RUNS_URL = "https://previous-runs-api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
KOLKATA = {"latitude": 22.5726, "longitude": 88.3639, "timezone": "Asia/Kolkata"}
DEFAULT_OUTPUT = ML_ROOT / "data" / "raw" / "kolkata_next_day.csv"
TIMEOUT_SECONDS = 180


def fetch_forecasts(start: str, end: str) -> pd.DataFrame:
    fields = ["temperature_2m", "relative_humidity_2m", "precipitation", "cloud_cover", "wind_speed_10m"]
    response = requests.get(
        PREVIOUS_RUNS_URL,
        params={
            **KOLKATA,
            "start_date": start,
            "end_date": end,
            "hourly": ",".join(f"{field}_previous_day1" for field in fields),
        },
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    hourly = pd.DataFrame(response.json()["hourly"])
    hourly["time"] = pd.to_datetime(hourly["time"])
    hourly["date"] = hourly["time"].dt.normalize()
    hourly.columns = [column.replace("_previous_day1", "") for column in hourly.columns]
    return (
        hourly.groupby("date")
        .agg(
            forecast_tmax=("temperature_2m", "max"),
            forecast_tmin=("temperature_2m", "min"),
            forecast_rh=("relative_humidity_2m", "mean"),
            forecast_rain=("precipitation", "sum"),
            forecast_peak_rain=("precipitation", "max"),
            forecast_cloud=("cloud_cover", "mean"),
            forecast_wind=("wind_speed_10m", "max"),
            hours=("temperature_2m", "count"),
        )
        .reset_index()
    )


def fetch_outcomes(start: str, end: str) -> pd.DataFrame:
    response = requests.get(
        ARCHIVE_URL,
        params={
            **KOLKATA,
            "start_date": start,
            "end_date": end,
            "daily": "temperature_2m_max,precipitation_sum",
            "models": "era5",
        },
        timeout=TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    daily = pd.DataFrame(response.json()["daily"]).rename(
        columns={
            "time": "date",
            "temperature_2m_max": "actual_tmax",
            "precipitation_sum": "actual_rain",
        }
    )
    daily["date"] = pd.to_datetime(daily["date"])
    return daily


def build_dataset(start: str, end: str) -> pd.DataFrame:
    frame = fetch_forecasts(start, end).merge(fetch_outcomes(start, end), on="date", how="inner")
    frame = frame[frame["hours"] == 24].drop(columns="hours")
    frame = frame.dropna().sort_values("date").reset_index(drop=True)
    day = frame["date"].dt.day_of_year
    frame["day_sin"] = np.sin(2 * np.pi * day / 365.25)
    frame["day_cos"] = np.cos(2 * np.pi * day / 365.25)
    # Earlier forecasts only: reanalysis arrives days late, so it can't be a live input.
    frame["forecast_rain_prev_3d"] = frame["forecast_rain"].shift(1).rolling(3).sum()
    return frame.dropna().reset_index(drop=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download the real next-day training dataset.")
    parser.add_argument("--start", default="2024-01-15")
    parser.add_argument("--end", required=True, help="Use a date at least 7 days ago; ERA5 arrives late.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)

    frame = build_dataset(args.start, args.end)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    print(f"wrote {len(frame)} real days, {frame['date'].min():%Y-%m-%d} to {frame['date'].max():%Y-%m-%d}: {output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
