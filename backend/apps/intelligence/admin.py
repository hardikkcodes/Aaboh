from django.contrib import admin

from .models import Recommendation, RecommendationEvidence


class RecommendationEvidenceInline(admin.TabularInline):
    model = RecommendationEvidence
    extra = 0
    readonly_fields = ("evidence_type", "label", "source", "observed_at", "reference", "source_url")


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ("title", "area", "kind", "severity", "generated_at")
    list_filter = ("severity", "kind", "area")
    search_fields = ("title", "body", "rule_id")
    readonly_fields = ("id", "generated_at")
    inlines = [RecommendationEvidenceInline]
