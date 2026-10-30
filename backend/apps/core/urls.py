from django.urls import path

from .views import DataStatusView, HealthView, ReadinessView, SystemConfigView

app_name = "core"

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("health/ready/", ReadinessView.as_view(), name="readiness"),
    path("system/config/", SystemConfigView.as_view(), name="system-config"),
    path("system/data-status/", DataStatusView.as_view(), name="data-status"),
]
