"""What the platform's models have actually achieved, from stored results and live counts."""

from __future__ import annotations

import json

from django.conf import settings

from apps.environment.models import EnvironmentalObservation
from apps.incidents.models import IncidentCategory, IncidentConfirmation, IncidentReport

WATERLOGGING_REPORT_TARGET = 300
WATERLOGGING_CLEAR_TARGET = 300
SATELLITE_OBSERVATION_TARGET = 500
TRAINING_REPORT = settings.REPO_ROOT / "ml" / "reports" / "next_day.json"


def _training_report() -> dict | None:
    try:
        return json.loads(TRAINING_REPORT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def build_model_status() -> dict:
    water_reports = IncidentReport.objects.filter(
        is_public=True, category__in=[IncidentCategory.WATERLOGGING, IncidentCategory.FLOODING]
    ).count()
    cleared = IncidentConfirmation.objects.filter(
        kind="cleared", incident__category__in=[IncidentCategory.WATERLOGGING, IncidentCategory.FLOODING]
    ).count()
    report = _training_report()
    return {
        "trained": report,
        "waiting": [
            {
                "key": "waterlogging",
                "name": "Street waterlogging prediction",
                "progress": [
                    {"label": "Water reports", "value": water_reports, "target": WATERLOGGING_REPORT_TARGET},
                    {"label": "Cleared confirmations", "value": cleared, "target": WATERLOGGING_CLEAR_TARGET},
                ],
                "note": "Needs real reports across a monsoon. Cleared votes teach the model when roads are dry.",
            },
            {
                "key": "land_surface_heat",
                "name": "Neighbourhood surface heat",
                "progress": [
                    {
                        "label": "Satellite observations",
                        "value": EnvironmentalObservation.objects.count(),
                        "target": SATELLITE_OBSERVATION_TARGET,
                    }
                ],
                "note": "Needs Google Earth Engine access to export Landsat data.",
            },
        ],
    }
