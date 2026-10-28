"""DRF building blocks for owner-scoped endpoints (AD-5).

Querysets come only from `Model.objects.for_user(request.user)`, so a foreign id is
indistinguishable from a missing one (404 `not_found` envelope, never 403). The owner is
always `request.user`; any client-supplied `owner` is ignored.
"""
from django.core.exceptions import ImproperlyConfigured
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .ownership import OwnedManager, OwnedModel


class OwnedQuerysetMixin:
    """Scopes the view's queryset to the requesting user.

    Subclasses set `model` to a concrete `OwnedModel` subclass (not `queryset`).
    """

    model = None
    permission_classes = [IsAuthenticated]
    # Stable order so pagination is deterministic.
    ordering = ("-created_at", "-pk")

    def get_owned_model(self):
        model = self.model
        if model is None or not issubclass(model, OwnedModel) or model._meta.abstract:
            raise ImproperlyConfigured(
                f"{type(self).__name__}.model must be a concrete OwnedModel subclass."
            )
        if not isinstance(model._default_manager, OwnedManager):
            raise ImproperlyConfigured(
                f"{model.__name__} default manager must be an OwnedManager."
            )
        return model

    def get_queryset(self):
        model = self.get_owned_model()
        return model._default_manager.for_user(self.request.user).order_by(*self.ordering)


class OwnedModelViewSet(OwnedQuerysetMixin, viewsets.ModelViewSet):
    """CRUD over the caller's own rows only."""

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        # Ownership never changes through the API, whatever the serializer exposes.
        serializer.save(owner=self.request.user)
