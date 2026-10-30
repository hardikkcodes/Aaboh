from django.contrib import admin

from .models import OfficialAlert


@admin.register(OfficialAlert)
class OfficialAlertAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "hazard", "severity", "status", "issued_at", "expires_at")
    list_filter = ("source", "hazard", "severity", "status")
    search_fields = ("title", "external_id", "areas_text")
    date_hierarchy = "issued_at"
    readonly_fields = ("id", "created_at", "updated_at")
