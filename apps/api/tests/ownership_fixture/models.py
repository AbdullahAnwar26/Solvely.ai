from django.db import models

from core.ownership import OwnedModel


class Note(OwnedModel):
    """Test-only concrete owned model."""

    title = models.CharField(max_length=200)

    def __str__(self):
        return f"Note(id={self.pk})"
