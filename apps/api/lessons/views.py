from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets

from core.viewsets import OwnedQuerysetMixin

from .models import Lesson
from .serializers import LessonCreateSerializer, LessonSerializer
from .throttles import LessonCreateRateThrottle

ERROR = OpenApiResponse(description="Error envelope (see core.errors).")


@extend_schema_view(
    list=extend_schema(summary="List my lessons, newest first", responses={200: LessonSerializer}),
    retrieve=extend_schema(
        summary="Get one of my lessons", responses={200: LessonSerializer, 404: ERROR}
    ),
    create=extend_schema(
        summary="Create a lesson with an empty Board",
        request=LessonCreateSerializer,
        responses={201: LessonSerializer, 400: ERROR, 429: ERROR},
    ),
)
class LessonViewSet(
    OwnedQuerysetMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Create, retrieve and list the caller's own Lessons. No update or delete in this story."""

    model = Lesson
    serializer_class = LessonSerializer

    def get_throttles(self):
        throttles = super().get_throttles()
        if getattr(self, "action", None) == "create":
            throttles.append(LessonCreateRateThrottle())
        return throttles

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
