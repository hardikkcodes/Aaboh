from django.urls import path

from .views import AirQualityMeasurementsView, AirQualityStationsView

app_name = "air_quality"

urlpatterns = [
    path("air-quality/stations/", AirQualityStationsView.as_view(), name="stations"),
    path("air-quality/measurements/", AirQualityMeasurementsView.as_view(), name="measurements"),
]
