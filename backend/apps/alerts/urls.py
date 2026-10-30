from django.urls import path

from .views import AlertDetailView, AlertListView

app_name = "alerts"

urlpatterns = [
    path("alerts/", AlertListView.as_view(), name="list"),
    path("alerts/<uuid:pk>/", AlertDetailView.as_view(), name="detail"),
]
