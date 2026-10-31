"""Real rain chances, counted from ensemble forecasts.

An ensemble runs the same forecast many times with small changes. The chance of rain
is the share of runs that produce it, so nothing here is a guess or a fixed rule.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import median, quantiles
from zoneinfo import ZoneInfo

from data_pipelines.providers.open_meteo import fetch_rain_ensemble

from apps.locations.models import Area

from .models import RainOutlook

IST = ZoneInfo("Asia/Kolkata")
WET_DAY_MM = 1
STEADY_DAY_MM = 10
HEAVY_DAY_MM = 50
WET_SPELL_MM = 0.5
BLOCK_HOURS = 3
BLOCKS = 8
MIN_MEMBERS = 10
PARTS = [("morning", 6, 12), ("afternoon", 12, 17), ("evening", 17, 21), ("night", 21, 30)]


def _percent(count: int, total: int) -> int:
    return round(100 * count / total)


def _chance(totals: list[float], threshold: float) -> int:
    return _percent(sum(value >= threshold for value in totals), len(totals))


def _totals(members: list[list[float | None]], indexes: list[int]) -> list[float]:
    return [sum(member[index] or 0 for index in indexes) for member in members]


def _day_summary(day: date, totals: list[float]) -> dict:
    low, _, high = quantiles(totals, n=4, method="inclusive") if len(totals) > 1 else (totals[0],) * 3
    return {
        "date": day.isoformat(),
        "chance_pct": _chance(totals, WET_DAY_MM),
        "steady_chance_pct": _chance(totals, STEADY_DAY_MM),
        "heavy_chance_pct": _chance(totals, HEAVY_DAY_MM),
        "typical_mm": round(median(totals), 1),
        "low_mm": round(low, 1),
        "high_mm": round(high, 1),
    }


def summarise(times: list[str], members: list[list[float | None]], now: datetime) -> dict:
    """Turn hourly runs into chances by day, by part of day and by the next few hours."""
    local = now.astimezone(IST).replace(tzinfo=None)
    moments = [datetime.fromisoformat(value) for value in times]
    current = local.replace(minute=0, second=0, microsecond=0)

    by_day = defaultdict(list)
    for index, moment in enumerate(moments):
        if moment >= current:
            by_day[moment.date()].append(index)
    days = [_day_summary(day, _totals(members, by_day[day])) for day in sorted(by_day)]

    parts = []
    for offset in (0, 1):
        day = current.date() + timedelta(days=offset)
        start_of_day = datetime.combine(day, datetime.min.time())
        for name, first, last in PARTS:
            start, end = start_of_day + timedelta(hours=first), start_of_day + timedelta(hours=last)
            indexes = [i for i, moment in enumerate(moments) if max(start, current) <= moment < end]
            if indexes:
                parts.append(
                    {
                        "day": "today" if offset == 0 else "tomorrow",
                        "part": name,
                        "chance_pct": _chance(_totals(members, indexes), WET_SPELL_MM),
                    }
                )

    blocks = []
    for number in range(BLOCKS):
        start = current + timedelta(hours=number * BLOCK_HOURS)
        end = start + timedelta(hours=BLOCK_HOURS)
        indexes = [i for i, moment in enumerate(moments) if start <= moment < end]
        if indexes:
            totals = _totals(members, indexes)
            blocks.append(
                {
                    "start": start.isoformat(),
                    "chance_pct": _chance(totals, WET_SPELL_MM),
                    "typical_mm": round(median(totals), 1),
                }
            )

    next_day = [i for i, moment in enumerate(moments) if current <= moment < current + timedelta(hours=24)]
    totals = _totals(members, next_day)
    return {
        "runs": len(members),
        "next_24h": {"chance_pct": _chance(totals, WET_DAY_MM), "typical_mm": round(median(totals), 1)},
        "days": days,
        "parts": parts,
        "blocks": blocks,
    }


def refresh_outlook(area: Area, *, now: datetime) -> RainOutlook | None:
    latitude, longitude = area.focus
    payload = fetch_rain_ensemble(latitude, longitude)
    hourly = payload["hourly"]
    members = [values for name, values in hourly.items() if name.startswith("precipitation")]
    if len(members) < MIN_MEMBERS:
        return None
    outlook, _ = RainOutlook.objects.update_or_create(
        area=area, defaults={"payload": summarise(hourly["time"], members, now)}
    )
    return outlook


def chance_at(area: Area, moment: datetime) -> int | None:
    """The chance of rain in the three hours around a moment, if it's in the forecast."""
    outlook = RainOutlook.objects.filter(area=area.data_area).first()
    if outlook is None:
        return None
    local = moment.astimezone(IST).replace(tzinfo=None)
    for block in outlook.payload["blocks"]:
        start = datetime.fromisoformat(block["start"])
        if start <= local < start + timedelta(hours=BLOCK_HOURS):
            return block["chance_pct"]
    return None
