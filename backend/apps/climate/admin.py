from django.contrib import admin

from .models import ClimateBaseline, ClimateMetric


@admin.register(ClimateBaseline)
class ClimateBaselineAdmin(admin.ModelAdmin):
    list_display = ("name", "variable", "start_year", "end_year", "value", "unit")
    search_fields = ("name", "variable")


@admin.register(ClimateMetric)
class ClimateMetricAdmin(admin.ModelAdmin):
    list_display = ("area", "variable", "period_type", "season", "period_start", "value", "unit", "anomaly")
    list_filter = ("dataset", "variable", "period_type", "season")
    date_hierarchy = "period_start"
    search_fields = ("area__name",)
