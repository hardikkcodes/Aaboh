from django.urls import path

from .views import (
    EnvironmentCellDetailView,
    EnvironmentLayersView,
    EnvironmentObservationsView,
    EnvironmentTerrainView,
)

app_name = "environment"

urlpatterns = [
    path("environment/terrain/", EnvironmentTerrainView.as_view(), name="terrain"),
    path("environment/layers/", EnvironmentLayersView.as_view(), name="layers"),
    path("environment/observations/", EnvironmentObservationsView.as_view(), name="observations"),
    path("environment/cells/<str:cell_code>/", EnvironmentCellDetailView.as_view(), name="cell-detail"),
]
