"""Root URL configuration. All application endpoints live under /api/v1/."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.core.urls")),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.locations.urls")),
    path("api/v1/", include("apps.weather.urls")),
    path("api/v1/", include("apps.alerts.urls")),
    path("api/v1/", include("apps.air_quality.urls")),
    path("api/v1/", include("apps.environment.urls")),
    path("api/v1/", include("apps.heat.urls")),
    path("api/v1/", include("apps.incidents.urls")),
    path("api/v1/", include("apps.rainfall.urls")),
    path("api/v1/", include("apps.climate.urls")),
    path("api/v1/", include("apps.intelligence.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
