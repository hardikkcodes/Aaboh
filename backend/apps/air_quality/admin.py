from django.contrib import admin

from .models import AQIMeasurement, AQIStation


@admin.register(AQIStation)
class AQIStationAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "source", "latitude", "longitude", "is_active")
    list_filter = ("source", "city", "is_active")
    search_fields = ("name", "external_id")


@admin.register(AQIMeasurement)
class AQIMeasurementAdmin(admin.ModelAdmin):
    list_display = ("station", "measured_at", "aqi", "pm25", "pm10", "quality_status")
    list_filter = ("quality_status", "source")
    date_hierarchy = "measured_at"
    search_fields = ("station__name",)
