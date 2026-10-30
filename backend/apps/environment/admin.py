from django.contrib import admin

from .models import EnvironmentalObservation, SatelliteScene


@admin.register(SatelliteScene)
class SatelliteSceneAdmin(admin.ModelAdmin):
    list_display = ("scene_id", "platform", "collection", "acquired_at", "cloud_cover_pct")
    list_filter = ("platform", "collection", "source")
    date_hierarchy = "acquired_at"
    search_fields = ("scene_id",)


@admin.register(EnvironmentalObservation)
class EnvironmentalObservationAdmin(admin.ModelAdmin):
    list_display = ("cell", "observed_on", "lst_c", "ndvi", "ndbi", "mndwi", "valid_pixel_fraction")
    list_filter = ("observed_on", "processing_version", "scene__platform")
    search_fields = ("cell__code", "scene__scene_id")
