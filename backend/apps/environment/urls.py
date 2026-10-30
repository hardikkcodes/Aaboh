from django.urls import path

from .views import EnvironmentCellDetailView, EnvironmentLayersView, EnvironmentObservationsView

app_name = "environment"

urlpatterns = [
    path("environment/layers/", EnvironmentLayersView.as_view(), name="layers"),
    path("environment/observations/", EnvironmentObservationsView.as_view(), name="observations"),
    path("environment/cells/<str:cell_code>/", EnvironmentCellDetailView.as_view(), name="cell-detail"),
]
