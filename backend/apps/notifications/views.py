from __future__ import annotations

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.core.schemas import DocumentedAPIView

from .models import Notification

LIST_LIMIT = 50


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "title", "body", "link", "read_at", "created_at"]


class NotificationListView(DocumentedAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = Notification.objects.filter(user=request.user)
        return Response(
            {
                "unread": items.filter(read_at__isnull=True).count(),
                "results": NotificationSerializer(items[:LIST_LIMIT], many=True).data,
            }
        )


class NotificationReadView(DocumentedAPIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None)
    def post(self, request):
        updated = Notification.objects.filter(user=request.user, read_at__isnull=True).update(
            read_at=timezone.now()
        )
        return Response({"marked_read": updated})
