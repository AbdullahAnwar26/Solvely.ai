from rest_framework import serializers

from .models import Lesson


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        # `owner` is deliberately absent: it is never accepted from the client.
        fields = ["id", "title", "current_revision", "created_at", "updated_at"]
        read_only_fields = ["id", "current_revision", "created_at", "updated_at"]


class LessonCreateSerializer(serializers.ModelSerializer):
    """Documents the create request body (OpenAPI only); responses use LessonSerializer."""

    class Meta:
        model = Lesson
        fields = ["title"]


# --- Board (Story 2.3) -------------------------------------------------------------------
# These serializers document the contract and parse the PUT envelope. The Board payload itself
# is checked strictly by `lessons.board.validate_board` (closed keys, closed element types,
# fixed limits), which DRF field types alone cannot express.


class BoardZoomSerializer(serializers.Serializer):
    value = serializers.FloatField()


class BoardAppStateSerializer(serializers.Serializer):
    # camelCase on purpose: these are Excalidraw's own appState keys, stored as they come.
    viewBackgroundColor = serializers.CharField(required=False)
    scrollX = serializers.FloatField(required=False)
    scrollY = serializers.FloatField(required=False)
    zoom = BoardZoomSerializer(required=False)


class BoardPayloadSerializer(serializers.Serializer):
    schema_version = serializers.IntegerField()
    elements = serializers.ListField(child=serializers.DictField())
    app_state = BoardAppStateSerializer(required=False)


class BoardStateSerializer(serializers.Serializer):
    """GET response: the latest revision number and its Board (revision 0 = empty Board)."""

    revision = serializers.IntegerField(min_value=0)
    board = BoardPayloadSerializer()


class BoardSaveRequestSerializer(serializers.Serializer):
    """PUT body as documented in OpenAPI."""

    base_revision = serializers.IntegerField(min_value=0)
    save_id = serializers.UUIDField()
    board = BoardPayloadSerializer()


class BoardSaveEnvelopeSerializer(serializers.Serializer):
    """Parses the PUT body at runtime. `board` stays raw JSON so it reaches the strict
    validator untouched (DRF field types would coerce or drop keys)."""

    base_revision = serializers.IntegerField(min_value=0)
    save_id = serializers.UUIDField()
    board = serializers.JSONField()


class BoardSaveResponseSerializer(serializers.Serializer):
    revision = serializers.IntegerField(min_value=1)
