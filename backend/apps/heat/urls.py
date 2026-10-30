from django.urls import path

from .views import HeatHotspotsView, HeatModelInfoView, HeatPredictionsView

app_name = "heat"

urlpatterns = [
    path("heat/predictions/", HeatPredictionsView.as_view(), name="predictions"),
    path("heat/hotspots/", HeatHotspotsView.as_view(), name="hotspots"),
    path("heat/model-info/", HeatModelInfoView.as_view(), name="model-info"),
]
