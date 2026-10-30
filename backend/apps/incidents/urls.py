from django.urls import path

from .views import (
    IncidentDetailView,
    IncidentHistoryView,
    IncidentListCreateView,
    IncidentModerateView,
    IncidentSummaryView,
)

app_name = "incidents"

urlpatterns = [
    path("incidents/", IncidentListCreateView.as_view(), name="list-create"),
    path("incidents/summary/", IncidentSummaryView.as_view(), name="summary"),
    path("incidents/<uuid:pk>/", IncidentDetailView.as_view(), name="detail"),
    path("incidents/<uuid:pk>/history/", IncidentHistoryView.as_view(), name="history"),
    path("incidents/<uuid:pk>/moderate/", IncidentModerateView.as_view(), name="moderate"),
]
