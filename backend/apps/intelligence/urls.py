from django.urls import path

from .views import InsightDetailView, InsightGenerateView, InsightHistoryView, InsightsView

app_name = "intelligence"

urlpatterns = [
    path("insights/", InsightsView.as_view(), name="list"),
    path("insights/generate/", InsightGenerateView.as_view(), name="generate"),
    path("insights/history/", InsightHistoryView.as_view(), name="history"),
    path("insights/<uuid:pk>/", InsightDetailView.as_view(), name="detail"),
]
