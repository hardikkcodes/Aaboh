from django.urls import path

from .views import AreaDetailView, AreaGridCellsView, AreaListView, LocationSearchView

app_name = "locations"

urlpatterns = [
    path("areas/", AreaListView.as_view(), name="area-list"),
    path("areas/<slug:slug>/", AreaDetailView.as_view(), name="area-detail"),
    path("areas/<slug:slug>/grid-cells/", AreaGridCellsView.as_view(), name="area-grid-cells"),
    path("locations/search/", LocationSearchView.as_view(), name="location-search"),
]
