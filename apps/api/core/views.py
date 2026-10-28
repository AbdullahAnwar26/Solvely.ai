from django.db import connection
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response

_HEALTH = inline_serializer("Health", {"status": serializers.ChoiceField(choices=["ok"])})
_READY = inline_serializer(
    "Ready", {"status": serializers.ChoiceField(choices=["ready", "unavailable"])}
)


@extend_schema(
    responses={200: OpenApiResponse(response=_HEALTH, description="Process is up.")}
)
@api_view(["GET"])
@throttle_classes([])
def health(request):
    """Liveness: process is up. Does not touch dependencies."""
    return Response({"status": "ok"})


@extend_schema(
    responses={
        200: OpenApiResponse(response=_READY, description="Database reachable."),
        503: OpenApiResponse(response=_READY, description="Database unavailable."),
    }
)
@api_view(["GET"])
@throttle_classes([])
def ready(request):
    """Readiness: database reachable. Failure detail is not leaked."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return Response({"status": "unavailable"}, status=503)
    return Response({"status": "ready"})
