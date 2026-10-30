from django.urls import path

from .views import WeatherCurrentView, WeatherForecastView, WeatherHistoryView, WeatherLocationsView

app_name = "weather"

urlpatterns = [
    path("weather/current/", WeatherCurrentView.as_view(), name="current"),
    path("weather/forecast/", WeatherForecastView.as_view(), name="forecast"),
    path("weather/history/", WeatherHistoryView.as_view(), name="history"),
    path("weather/locations/", WeatherLocationsView.as_view(), name="locations"),
]
