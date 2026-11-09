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
