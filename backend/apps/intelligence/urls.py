from django.urls import path

from .views import (
    AreaPlaceStatusView,
    InsightDetailView,
    InsightGenerateView,
    InsightHistoryView,
    InsightsView,
    ModelStatusView,
    PlaceStatusView,
    TodayView,
    WeekPlanView,
)

app_name = "intelligence"

urlpatterns = [
    path("insights/", InsightsView.as_view(), name="list"),
    path("insights/generate/", InsightGenerateView.as_view(), name="generate"),
    path("insights/history/", InsightHistoryView.as_view(), name="history"),
    path("insights/<uuid:pk>/", InsightDetailView.as_view(), name="detail"),
    path("today/", TodayView.as_view(), name="today"),
    path("system/models/", ModelStatusView.as_view(), name="model-status"),
    path("planner/week/", WeekPlanView.as_view(), name="week-plan"),
    path("place-status/", PlaceStatusView.as_view(), name="place-status"),
    path(
        "areas/<slug:slug>/place-status/",
        AreaPlaceStatusView.as_view(),
        name="area-place-status",
    ),
]
