from django.urls import path

from .views import RainfallForecastView, RainfallHistoryView

app_name = "rainfall"

urlpatterns = [
    path("rainfall/forecast/", RainfallForecastView.as_view(), name="forecast"),
    path("rainfall/history/", RainfallHistoryView.as_view(), name="history"),
]
