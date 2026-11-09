import uuid

from django.db import models

from core import limits
from core.ownership import OwnedModel


class Lesson(OwnedModel):
    """A Learner's Lesson. Revision 0 means the empty Board (no BoardRevision rows yet)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=limits.LESSON_TITLE_MAX_LENGTH, default="Untitled lesson")
    current_revision = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Lesson(id={self.pk})"
