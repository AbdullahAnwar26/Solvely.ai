"""Owner-scoped data foundation (AD-5).

Every model holding per-learner data subclasses `OwnedModel`. Its default manager is
`OwnedManager`, and views reach rows only through `Model.objects.for_user(request.user)`.
"""
from django.conf import settings
from django.db import models


class OwnedQuerySet(models.QuerySet):
    def for_user(self, user):
        """Rows owned by `user`; anonymous or missing users get an empty queryset."""
        if user is None or not getattr(user, "is_authenticated", False):
            return self.none()
        return self.filter(owner=user)


class OwnedManager(models.Manager.from_queryset(OwnedQuerySet)):
    """Default manager of every OwnedModel; exposes `for_user(user)`."""


class OwnedModel(models.Model):
    """Abstract base for owned data. The owner is always set server-side from request.user."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_index=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OwnedManager()

    class Meta:
        abstract = True
