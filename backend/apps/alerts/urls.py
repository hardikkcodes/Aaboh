from django.urls import path

from .views import AlertDetailView, AlertListView, CycloneListView

app_name = "alerts"

urlpatterns = [
    path("cyclones/", CycloneListView.as_view(), name="cyclones"),
    path("alerts/", AlertListView.as_view(), name="list"),
    path("alerts/<uuid:pk>/", AlertDetailView.as_view(), name="detail"),
]
