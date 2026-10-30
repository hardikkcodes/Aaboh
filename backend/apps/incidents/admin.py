from django.contrib import admin

from .models import IncidentAttachment, IncidentReport, IncidentStatusHistory


class IncidentAttachmentInline(admin.TabularInline):
    model = IncidentAttachment
    extra = 0
    readonly_fields = ("id", "original_name", "content_type", "size_bytes", "sha256", "created_at")


class IncidentStatusHistoryInline(admin.TabularInline):
    model = IncidentStatusHistory
    extra = 0
    readonly_fields = ("from_status", "to_status", "changed_by", "note", "created_at")
    can_delete = False


@admin.register(IncidentReport)
class IncidentReportAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "status", "area", "occurred_at", "created_at", "is_public")
    list_filter = ("status", "category", "area", "is_public")
    search_fields = ("description", "address_text", "neighbourhood__name")
    date_hierarchy = "created_at"
    readonly_fields = ("id", "created_at", "updated_at", "verified_at", "resolved_at")
    inlines = [IncidentAttachmentInline, IncidentStatusHistoryInline]


@admin.register(IncidentAttachment)
class IncidentAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "incident", "content_type", "size_bytes", "created_at")
    readonly_fields = ("id", "sha256", "created_at")
