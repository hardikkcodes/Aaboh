from __future__ import annotations

from rest_framework import serializers

from .models import Area, GridCell, Neighbourhood


class SourceSummarySerializer(serializers.Serializer):
    slug = serializers.CharField()
    name = serializers.CharField()
    provider_type = serializers.CharField()
    attribution = serializers.CharField()
    license_name = serializers.CharField()


class NeighbourhoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = Neighbourhood
        fields = ["id", "name", "slug", "latitude", "longitude", "source_ref"]


class GridCellSerializer(serializers.ModelSerializer):
    version = serializers.CharField(source="definition.version", read_only=True)

    class Meta:
        model = GridCell
        fields = [
            "id",
            "code",
            "version",
            "row",
            "col",
            "geometry",
            "full_geometry",
            "centroid",
            "centroid_lat",
            "centroid_lon",
            "coverage_fraction",
            "area_km2",
        ]


class GridCellCompactSerializer(GridCellSerializer):
    class Meta(GridCellSerializer.Meta):
        fields = ["id", "code", "row", "col", "centroid", "centroid_lat", "centroid_lon", "coverage_fraction"]


class AreaListSerializer(serializers.ModelSerializer):
    source = serializers.SerializerMethodField()
    neighbourhood_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Area
        fields = [
            "id",
            "slug",
            "name",
            "level",
            "centroid",
            "centroid_lat",
            "centroid_lon",
            "area_km2",
            "source",
            "source_ref",
            "neighbourhood_count",
        ]

    def get_source(self, obj) -> dict | None:
        if not obj.source:
            return None
        return {
            "slug": obj.source.slug,
            "name": obj.source.name,
            "provider_type": obj.source.provider_type,
            "attribution": obj.source.attribution,
            "license_name": obj.source.license_name,
        }


class AreaDetailSerializer(AreaListSerializer):
    boundary = serializers.JSONField(read_only=True)
    neighbourhoods = NeighbourhoodSerializer(many=True, read_only=True)
    grid_versions = serializers.SerializerMethodField()

    class Meta(AreaListSerializer.Meta):
        fields = AreaListSerializer.Meta.fields + ["boundary", "neighbourhoods", "grid_versions", "metadata"]

    def get_grid_versions(self, obj) -> list[dict]:
        return [
            {
                "version": definition.version,
                "cell_size_m": definition.cell_size_m,
                "crs": definition.crs,
                "cell_count": definition.cell_count,
                "created_at": definition.created_at,
            }
            for definition in obj.grid_definitions.all()
        ]
