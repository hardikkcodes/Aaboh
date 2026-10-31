from django.urls import path

from .views import ApiRootView, DataStatusView, HealthView, ReadinessView, SystemConfigView

app_name = "core"

urlpatterns = [
    path("", ApiRootView.as_view(), name="api-root"),
    path("health/", HealthView.as_view(), name="health"),
    path("health/ready/", ReadinessView.as_view(), name="readiness"),
    path("system/config/", SystemConfigView.as_view(), name="system-config"),
    path("system/data-status/", DataStatusView.as_view(), name="data-status"),
]
