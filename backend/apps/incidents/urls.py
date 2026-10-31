from django.urls import path

from .views import (
    CommunitySpotDetailView,
    CommunitySpotListCreateView,
    IncidentConfirmView,
    IncidentDetailView,
    IncidentExportView,
    IncidentHistoryView,
    IncidentListCreateView,
    IncidentLiveMapView,
    IncidentModerateView,
    IncidentStatsView,
    IncidentSummaryView,
)

app_name = "incidents"

urlpatterns = [
    path("incidents/", IncidentListCreateView.as_view(), name="list-create"),
    path("incidents/live/", IncidentLiveMapView.as_view(), name="live"),
    path("incidents/stats/", IncidentStatsView.as_view(), name="stats"),
    path("incidents/export/", IncidentExportView.as_view(), name="export"),
    path("incidents/summary/", IncidentSummaryView.as_view(), name="summary"),
    path("incidents/<uuid:pk>/", IncidentDetailView.as_view(), name="detail"),
    path("incidents/<uuid:pk>/confirm/", IncidentConfirmView.as_view(), name="confirm"),
    path("incidents/<uuid:pk>/history/", IncidentHistoryView.as_view(), name="history"),
    path("incidents/<uuid:pk>/moderate/", IncidentModerateView.as_view(), name="moderate"),
    path("spots/", CommunitySpotListCreateView.as_view(), name="spots"),
    path("spots/<uuid:pk>/", CommunitySpotDetailView.as_view(), name="spot-detail"),
]
