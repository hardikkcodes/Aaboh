"""Portable GeoJSON model field.

Stores validated GeoJSON in a JSON column. This keeps model definitions stable
across SQLite (development) and PostgreSQL (production) while the project
migrates to native PostGIS geometry columns (see docs/DECISIONS.md ADR-003).
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models

from .geometry import validate_geometry


class GeometryField(models.JSONField):
    def __init__(self, *args, geom_type: str | None = None, allowed_types: tuple[str, ...] | None = None, **kwargs):
        self.geom_type = geom_type
        self.allowed_types = allowed_types or ((geom_type,) if geom_type else None)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.allowed_types:
            kwargs["allowed_types"] = self.allowed_types
        return name, path, args, kwargs

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if value in self.empty_values:
            return
        try:
            validate_geometry(value, self.allowed_types)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    def get_prep_value(self, value):
        return super().get_prep_value(value)
