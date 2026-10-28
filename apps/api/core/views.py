from django.db import connection
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.response import Response


@extend_schema(responses={200: OpenApiResponse(description="Process is up.")})
@api_view(["GET"])
@throttle_classes([])
def health(request):
    """Liveness: process is up. Does not touch dependencies."""
    return Response({"status": "ok"})


@extend_schema(
    responses={
        200: OpenApiResponse(description="Database reachable."),
        503: OpenApiResponse(description="Database unavailable."),
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
