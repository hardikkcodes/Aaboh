from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.core.fields import GeometryField
from apps.core.geometry import centroid_point, geodesic_area_km2, parse_geometry, point_geojson


class AreaLevel(models.TextChoices):
    CITY = "city", "City / municipal corporation"
    DISTRICT = "district", "District"
    ZONE = "zone", "City zone"
    WARD = "ward", "Ward"
    NEIGHBOURHOOD = "neighbourhood", "Neighbourhood"


class Area(models.Model):
    """A governed geographic area (initially Kolkata Municipal Corporation)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    level = models.CharField(max_length=24, choices=AreaLevel.choices, default=AreaLevel.CITY)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children"
    )
    boundary = GeometryField(allowed_types=("Polygon", "MultiPolygon"))
    centroid = GeometryField(geom_type="Point")
    centroid_lat = models.FloatField()
    centroid_lon = models.FloatField()
    area_km2 = models.FloatField()
    source = models.ForeignKey(
        "core.DataSource", on_delete=models.PROTECT, null=True, blank=True, related_name="areas"
    )
    source_ref = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["level", "is_active"], name="area_level_active_idx")]

    @property
    def data_area(self) -> Area:
        """Zones share their parent's reports, grid and climate records."""
        return self.parent if self.level == AreaLevel.ZONE and self.parent_id else self

    @property
    def focus(self) -> tuple[float, float]:
        """Where people are. A district's centre can be far from them, even in open water."""
        point = self.metadata.get("forecast_point")
        return (point[0], point[1]) if point else (self.centroid_lat, self.centroid_lon)

    def covers(self, latitude: float, longitude: float) -> bool:
        return parse_geometry(self.boundary).covers(parse_geometry(point_geojson(latitude, longitude)))

    def clean(self):
        geom = parse_geometry(self.boundary)
        if geodesic_area_km2(geom) <= 0:
            raise ValidationError({"boundary": "Area boundary must have a positive area."})
        point = centroid_point(self.boundary)
        if abs(point.y - self.centroid_lat) > 1e-6 or abs(point.x - self.centroid_lon) > 1e-6:
            raise ValidationError({"centroid": "Centroid coordinates disagree with the boundary."})

    def save(self, *args, **kwargs):
        if self.boundary:
            point = centroid_point(self.boundary)
            self.centroid = {"type": "Point", "coordinates": [point.x, point.y]}
            self.centroid_lat, self.centroid_lon = point.y, point.x
            self.area_km2 = geodesic_area_km2(self.boundary)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


class Neighbourhood(models.Model):
    """A named locality inside an area. Boundary is optional when OSM only has points."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="neighbourhoods")
    slug = models.SlugField(max_length=120)
    name = models.CharField(max_length=160)
    point = GeometryField(geom_type="Point")
    latitude = models.FloatField()
    longitude = models.FloatField()
    boundary = GeometryField(
        allowed_types=("Polygon", "MultiPolygon"), null=True, blank=True
    )
    source = models.ForeignKey(
        "core.DataSource", on_delete=models.PROTECT, null=True, blank=True, related_name="neighbourhoods"
    )
    source_ref = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["area", "slug"], name="uniq_neighbourhood_slug_per_area")
        ]
        indexes = [
            models.Index(fields=["area", "is_active"], name="neighbourhood_area_active_idx"),
            models.Index(fields=["name"], name="neighbourhood_name_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.area.slug})"


class GridDefinition(models.Model):
    """Versioned generation parameters for a deterministic analytical grid."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="grid_definitions")
    version = models.CharField(max_length=40)
    cell_size_m = models.PositiveIntegerField(default=1000)
    crs = models.CharField(max_length=20, default="EPSG:32645")
    origin_x = models.FloatField()
    origin_y = models.FloatField()
    cell_count = models.PositiveIntegerField(default=0)
    parameters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["area", "version"], name="uniq_grid_version_per_area")
        ]

    def __str__(self) -> str:
        return f"{self.area.slug} {self.version}"


class GridCell(models.Model):
    """An analytical aggregation unit — not the native resolution of any dataset."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    definition = models.ForeignKey(GridDefinition, on_delete=models.CASCADE, related_name="cells")
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="grid_cells")
    code = models.CharField(max_length=80, unique=True)
    row = models.PositiveIntegerField()
    col = models.PositiveIntegerField()
    geometry = GeometryField(allowed_types=("Polygon", "MultiPolygon"))
    full_geometry = GeometryField(allowed_types=("Polygon", "MultiPolygon"))
    centroid = GeometryField(geom_type="Point")
    centroid_lat = models.FloatField()
    centroid_lon = models.FloatField()
    coverage_fraction = models.FloatField()
    area_km2 = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["row", "col"]
        constraints = [
            models.UniqueConstraint(
                fields=["definition", "row", "col"], name="uniq_grid_cell_row_col_per_definition"
            )
        ]
        indexes = [
            models.Index(fields=["area", "definition"], name="gridcell_area_definition_idx"),
            models.Index(fields=["code"], name="gridcell_code_idx"),
            models.Index(fields=["centroid_lat", "centroid_lon"], name="gridcell_centroid_idx"),
        ]

    def __str__(self) -> str:
        return self.code
