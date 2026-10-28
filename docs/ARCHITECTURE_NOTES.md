# Architecture Notes

## Adding an owned model and endpoint (AD-5)

1. Subclass `core.ownership.OwnedModel` (gives `owner`, `created_at`, `updated_at`). Keep its default manager: `objects` must stay an `OwnedManager`.
2. Never put `owner` in a serializer's writable fields; the owner is always `request.user`.
3. Serve it with `core.viewsets.OwnedModelViewSet`, setting `model = YourModel` (not `queryset`). It requires authentication, scopes every query through `for_user(request.user)`, returns the 404 `not_found` envelope for foreign or missing ids, and sets the owner on create/update.
4. In any other code path, fetch rows only via `YourModel.objects.for_user(user)`.
5. Register the endpoint in `apps/api/tests/isolation.py` with `register_owned_endpoint(model, url, make=..., create_payload=..., update_payload=...)`. The shared cross-user checks in `tests/test_ownership.py` then run against it; an unregistered concrete `OwnedModel` fails the guard test.
6. Account deletion (Story 1.5) relies on `on_delete=CASCADE` from `owner`; keep it.
