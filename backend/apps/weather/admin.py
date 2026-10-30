from django.contrib import admin

from .models import WeatherLocation, WeatherRecord


@admin.register(WeatherLocation)
class WeatherLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "area", "source", "latitude", "longitude")
    list_filter = ("source", "area")


@admin.register(WeatherRecord)
class WeatherRecordAdmin(admin.ModelAdmin):
    list_display = ("location", "kind", "valid_time", "temperature_c", "precipitation_mm", "retrieved_at")
    list_filter = ("kind", "source", "quality_status")
    date_hierarchy = "valid_time"
    search_fields = ("location__name",)
