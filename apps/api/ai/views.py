from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .factory import PROVIDERS, provider_status


class AIStatusSerializer(serializers.Serializer):
    configured = serializers.BooleanField()
    provider = serializers.ChoiceField(choices=PROVIDERS)
    model = serializers.CharField(allow_null=True)
    max_attempts = serializers.IntegerField()
    max_concurrency = serializers.IntegerField()


class AIStatusView(APIView):
    """Staff-only provider diagnostics. Never returns the API key or any part of it."""

    permission_classes = [IsAdminUser]

    @extend_schema(
        operation_id="ai_status",
        responses={
            200: AIStatusSerializer,
            403: OpenApiResponse(description="Error envelope: anonymous or not staff."),
        },
    )
    def get(self, request):
        return Response(AIStatusSerializer(provider_status()).data)
