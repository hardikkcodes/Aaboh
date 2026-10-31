from django.urls import path

from .views import HeatGuideView, HeatHotspotsView, HeatModelInfoView, HeatPlaceView, HeatPredictionsView

app_name = "heat"

urlpatterns = [
    path("heat/predictions/", HeatPredictionsView.as_view(), name="predictions"),
    path("heat/guide/", HeatGuideView.as_view(), name="guide"),
    path("heat/place/", HeatPlaceView.as_view(), name="place"),
    path("heat/hotspots/", HeatHotspotsView.as_view(), name="hotspots"),
    path("heat/model-info/", HeatModelInfoView.as_view(), name="model-info"),
]
