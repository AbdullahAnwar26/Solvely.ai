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


class BoardRevision(OwnedModel):
    """One saved state of a Lesson's Board (AD-4).

    Rows are append-only: a save inserts revision `base + 1` and never updates an existing row.
    Old rows are removed only by the pruning policy (`limits.BOARD_REVISIONS_KEPT`). Revision 0
    is implicit (the empty Board) and has no row. The owner always mirrors the Lesson's owner.
    """

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="revisions")
    revision = models.PositiveIntegerField()
    payload = models.JSONField()
    # Client-chosen id of the save attempt; a retry with the same id is idempotent.
    save_id = models.UUIDField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["lesson", "revision"], name="board_revision_unique_number"
            ),
            models.UniqueConstraint(
                fields=["lesson", "save_id"], name="board_revision_unique_save_id"
            ),
        ]

    def __str__(self):
        return f"BoardRevision(lesson={self.lesson_id}, revision={self.revision})"
