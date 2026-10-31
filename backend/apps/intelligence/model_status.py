"""What the platform's models have actually achieved, from stored results and live counts."""

from __future__ import annotations

import json

from django.conf import settings

from apps.incidents.models import IncidentCategory, IncidentConfirmation, IncidentReport

WATERLOGGING_REPORT_TARGET = 300
WATERLOGGING_CLEAR_TARGET = 300
REPORTS = settings.REPO_ROOT / "ml" / "reports"


def _report(name: str) -> dict | None:
    try:
        return json.loads((REPORTS / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def build_model_status() -> dict:
    water_reports = IncidentReport.objects.filter(
        is_public=True, category__in=[IncidentCategory.WATERLOGGING, IncidentCategory.FLOODING]
    ).count()
    cleared = IncidentConfirmation.objects.filter(
        kind="cleared", incident__category__in=[IncidentCategory.WATERLOGGING, IncidentCategory.FLOODING]
    ).count()
    return {
        "trained": _report("next_day.json"),
        "surface_heat": _report("land_surface_heat.json"),
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
        ],
    }
