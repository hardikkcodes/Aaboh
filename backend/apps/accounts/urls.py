from django.urls import path

from .views import (
    LoginView,
    LogoutView,
    MeView,
    PreferenceView,
    RegisterView,
    SavedLocationDetailView,
    SavedLocationListCreateView,
)

app_name = "accounts"

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("users/me/", MeView.as_view(), name="me"),
    path("users/me/preferences/", PreferenceView.as_view(), name="preferences"),
    path(
        "users/me/saved-locations/",
        SavedLocationListCreateView.as_view(),
        name="saved-locations",
    ),
    path(
        "users/me/saved-locations/<uuid:pk>/",
        SavedLocationDetailView.as_view(),
        name="saved-location-detail",
    ),
]
