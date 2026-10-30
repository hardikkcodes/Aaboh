from django.urls import path

from .views import ClimateMetricsView, ClimateTrendsView

app_name = "climate"

urlpatterns = [
    path("climate/metrics/", ClimateMetricsView.as_view(), name="metrics"),
    path("climate/trends/", ClimateTrendsView.as_view(), name="trends"),
]
