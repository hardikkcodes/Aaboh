from __future__ import annotations

from django.db.models import Count, Q
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.schemas import DocumentedAPIView

from .models import Area, GridCell, Neighbourhood
from .serializers import AreaDetailSerializer, AreaListSerializer, GridCellSerializer


class AreaListView(ListAPIView):
    serializer_class = AreaListSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        queryset = (
            Area.objects.filter(is_active=True)
            .select_related("source")
            .annotate(neighbourhood_count=Count("neighbourhoods", filter=Q(neighbourhoods__is_active=True)))
        )
        level = self.request.query_params.get("level")
        if level:
            queryset = queryset.filter(level=level)
        return queryset


class AreaDetailView(RetrieveAPIView):
    serializer_class = AreaDetailSerializer
    permission_classes = [AllowAny]
    lookup_field = "slug"
    queryset = (
        Area.objects.filter(is_active=True)
        .select_related("source")
        .annotate(neighbourhood_count=Count("neighbourhoods", filter=Q(neighbourhoods__is_active=True)))
        .prefetch_related("neighbourhoods", "grid_definitions")
    )


class AreaGridCellsView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request, slug):
        try:
            area = Area.objects.get(slug=slug, is_active=True)
        except Area.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Area not found.", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )

        version = request.query_params.get("version")
        definitions = area.grid_definitions.all()
        definition = definitions.filter(version=version).first() if version else definitions.first()
        if definition is None:
            return Response(
                {
                    "area": {"slug": area.slug, "name": area.name},
                    "version": version,
                    "available_versions": [],
                    "count": 0,
                    "cells": [],
                    "detail": "No analytical grid has been generated for this area.",
                }
            )

        cells = GridCell.objects.filter(definition=definition).order_by("row", "col")
        return Response(
            {
                "area": {"slug": area.slug, "name": area.name},
                "version": definition.version,
                "cell_size_m": definition.cell_size_m,
                "crs": definition.crs,
                "available_versions": list(definitions.values_list("version", flat=True)),
                "count": cells.count(),
                "cells": GridCellSerializer(cells, many=True).data,
            }
        )


class LocationSearchView(DocumentedAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        results: list[dict] = []

        if len(query) >= 2:
            areas = Area.objects.filter(is_active=True, name__icontains=query)[:8]
            for area in areas:
                results.append(
                    {
                        "type": "area",
                        "id": str(area.id),
                        "name": area.name,
                        "slug": area.slug,
                        "area_slug": area.slug,
                        "latitude": area.centroid_lat,
                        "longitude": area.centroid_lon,
                    }
                )
            neighbourhoods = (
                Neighbourhood.objects.filter(is_active=True, name__icontains=query)
                .select_related("area")[:20]
            )
            for item in neighbourhoods:
                results.append(
                    {
                        "type": "neighbourhood",
                        "id": str(item.id),
                        "name": item.name,
                        "slug": item.slug,
                        "area_slug": item.area.slug,
                        "latitude": item.latitude,
                        "longitude": item.longitude,
                    }
                )
        else:
            neighbourhoods = (
                Neighbourhood.objects.filter(is_active=True).select_related("area").order_by("name")[:20]
            )
            for item in neighbourhoods:
                results.append(
                    {
                        "type": "neighbourhood",
                        "id": str(item.id),
                        "name": item.name,
                        "slug": item.slug,
                        "area_slug": item.area.slug,
                        "latitude": item.latitude,
                        "longitude": item.longitude,
                    }
                )

        return Response({"query": query, "count": len(results), "results": results})
