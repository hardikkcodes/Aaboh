from django.urls import path

from .views import (
    ChangePasswordView,
    ImpactView,
    LoginView,
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PreferenceView,
    RegisterView,
    ResendVerificationView,
    SavedLocationDetailView,
    SavedLocationListCreateView,
    SavedRouteDetailView,
    SavedRouteListCreateView,
    SavedRouteStatusView,
    VerifyEmailView,
)

app_name = "accounts"

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("auth/password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("auth/password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("auth/change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("auth/verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("auth/verify-email/resend/", ResendVerificationView.as_view(), name="verify-email-resend"),
    path("users/me/", MeView.as_view(), name="me"),
    path("users/me/preferences/", PreferenceView.as_view(), name="preferences"),
    path("users/me/impact/", ImpactView.as_view(), name="impact"),
    path("users/me/routes/", SavedRouteListCreateView.as_view(), name="routes"),
    path("users/me/routes/<uuid:pk>/", SavedRouteDetailView.as_view(), name="route-detail"),
    path("users/me/routes/<uuid:pk>/status/", SavedRouteStatusView.as_view(), name="route-status"),
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
