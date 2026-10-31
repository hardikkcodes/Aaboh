from django.urls import path

from .views import NotificationListView, NotificationReadView

app_name = "notifications"

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="list"),
    path("notifications/read/", NotificationReadView.as_view(), name="read"),
]
