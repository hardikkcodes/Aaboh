from django.contrib import admin

from .models import DataSource, IngestionRun


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "provider_type", "is_active", "expected_refresh_minutes")
    list_filter = ("provider_type", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = ("source", "status", "started_at", "finished_at", "records_written")
    list_filter = ("status", "source")
    date_hierarchy = "started_at"
    readonly_fields = ("id", "started_at")
