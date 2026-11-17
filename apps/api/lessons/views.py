from django.db import transaction
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core import limits
from core.errors import PayloadTooLarge
from core.viewsets import OwnedQuerysetMixin

from .board import RevisionConflict, empty_board, validate_board
from .models import BoardRevision, Lesson
from .serializers import (
    BoardSaveEnvelopeSerializer,
    BoardSaveRequestSerializer,
    BoardSaveResponseSerializer,
    BoardStateSerializer,
    LessonCreateSerializer,
    LessonSerializer,
)
from .throttles import BoardSaveRateThrottle, LessonCreateRateThrottle

ERROR = OpenApiResponse(description="Error envelope (see core.errors).")
CONFLICT = OpenApiResponse(
    description=(
        "Error envelope with code `revision_conflict` and `current_revision`: the save was "
        "based on an older revision and nothing was written."
    )
)


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
    """Create, retrieve and list the caller's own Lessons, and read or save their Board.

    No Lesson update or delete yet.
    """

    model = Lesson
    serializer_class = LessonSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, "action", None) == "save_board":
            # The Lesson row is the per-Board lock: saves on one Lesson run one at a time.
            queryset = queryset.select_for_update()
        return queryset

    def get_throttles(self):
        throttles = super().get_throttles()
        current = getattr(self, "action", None)
        if current == "create":
            throttles.append(LessonCreateRateThrottle())
        elif current == "save_board":
            throttles.append(BoardSaveRateThrottle())
        return throttles

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @extend_schema(
        summary="Get the latest Board revision of my lesson (revision 0 is the empty Board)",
        responses={200: BoardStateSerializer, 404: ERROR},
    )
    @action(detail=True, methods=["get"], url_path="board")
    def board(self, request, pk=None):
        lesson = self.get_object()
        latest = (
            BoardRevision.objects.for_user(request.user)
            .filter(lesson=lesson)
            .order_by("-revision")
            .first()
        )
        if latest is None:
            return Response({"revision": 0, "board": empty_board()})
        return Response({"revision": latest.revision, "board": latest.payload})

    @extend_schema(
        summary="Save my lesson's Board as a new revision",
        description=(
            "Optimistic concurrency (AD-4): `base_revision` must equal the Lesson's current "
            "revision, otherwise 409 `revision_conflict` and nothing is written. Repeating a "
            "save with the same `save_id` returns the revision it created (idempotent retry)."
        ),
        request=BoardSaveRequestSerializer,
        responses={
            200: BoardSaveResponseSerializer,
            400: ERROR,
            404: ERROR,
            409: CONFLICT,
            413: ERROR,
            429: ERROR,
        },
    )
    @board.mapping.put
    def save_board(self, request, pk=None):
        try:
            length = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            length = 0
        if length > limits.BOARD_MAX_BODY_BYTES:
            raise PayloadTooLarge()

        envelope = BoardSaveEnvelopeSerializer(data=request.data)
        envelope.is_valid(raise_exception=True)
        base_revision = envelope.validated_data["base_revision"]
        save_id = envelope.validated_data["save_id"]
        board = envelope.validated_data["board"]

        with transaction.atomic():
            lesson = self.get_object()  # owner-scoped and locked (select_for_update)
            revisions = BoardRevision.objects.for_user(request.user).filter(lesson=lesson)

            existing = revisions.filter(save_id=save_id).first()
            if existing is not None:
                return Response({"revision": existing.revision})
            if base_revision != lesson.current_revision:
                raise RevisionConflict(lesson.current_revision)

            validate_board(board)
            new_revision = base_revision + 1
            BoardRevision.objects.create(
                owner=lesson.owner,
                lesson=lesson,
                revision=new_revision,
                payload=board,
                save_id=save_id,
            )
            lesson.current_revision = new_revision
            lesson.save(update_fields=["current_revision", "updated_at"])
            # Pruning by policy, never by update: drop rows beyond the newest N.
            revisions.filter(revision__lte=new_revision - limits.BOARD_REVISIONS_KEPT).delete()
        return Response({"revision": new_revision})
