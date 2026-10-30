from django.contrib import admin

from .models import CellPrediction, ModelVersion, PredictionRun


@admin.register(ModelVersion)
class ModelVersionAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "algorithm", "task", "is_active", "is_operational", "trained_at")
    list_filter = ("task", "algorithm", "is_active", "is_operational")
    readonly_fields = ("id", "created_at")


@admin.register(PredictionRun)
class PredictionRunAdmin(admin.ModelAdmin):
    list_display = ("model_version", "area", "status", "generated_at")
    list_filter = ("status", "area")
    readonly_fields = ("id", "generated_at")


@admin.register(CellPrediction)
class CellPredictionAdmin(admin.ModelAdmin):
    list_display = ("cell", "run", "predicted_lst_c")
    search_fields = ("cell__code",)
