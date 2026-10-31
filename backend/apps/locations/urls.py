from django.urls import path

from .views import (
    AreaDetailView,
    AreaGridCellsView,
    AreaListView,
    LocationSearchView,
    NearestPlaceView,
    PlaceAutocompleteView,
    PlaceDetailsView,
    RoutePlanView,
)

app_name = "locations"

urlpatterns = [
    path("areas/", AreaListView.as_view(), name="area-list"),
    path("areas/<slug:slug>/", AreaDetailView.as_view(), name="area-detail"),
    path("areas/<slug:slug>/grid-cells/", AreaGridCellsView.as_view(), name="area-grid-cells"),
    path("places/autocomplete/", PlaceAutocompleteView.as_view(), name="place-autocomplete"),
    path("places/details/", PlaceDetailsView.as_view(), name="place-details"),
    path("routes/plan/", RoutePlanView.as_view(), name="route-plan"),
    path("locations/search/", LocationSearchView.as_view(), name="location-search"),
    path("locations/nearest/", NearestPlaceView.as_view(), name="location-nearest"),
]
