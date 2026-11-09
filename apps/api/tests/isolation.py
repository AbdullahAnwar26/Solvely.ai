"""Cross-user isolation harness (AD-5).

Every concrete `OwnedModel` must be registered here with the endpoint that serves it.
`test_ownership.py` runs the shared isolation checks against every registration, and a
guard test fails if a concrete OwnedModel is missing from the registry or does not use
`OwnedManager` as its default manager.

To add an owned endpoint, call `register_owned_endpoint(...)` in the "Registered owned
endpoints" section at the bottom of this module.
"""
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from django.apps import apps

from core.ownership import OwnedManager, OwnedModel

ALL_ACTIONS = frozenset({"list", "retrieve", "create", "update", "delete"})


@dataclass(frozen=True)
class OwnedEndpoint:
    model: type
    # Collection URL, e.g. "/api/v1/lessons/". Detail URLs are f"{url}{pk}/".
    url: str
    # Creates one row owned by the given user and returns it.
    make: Callable
    # Valid POST body (without `owner`) and a valid PATCH/PUT body.
    create_payload: dict = field(default_factory=dict)
    update_payload: dict = field(default_factory=dict)
    # Actions the endpoint serves; checks for other actions are skipped.
    actions: frozenset = ALL_ACTIONS

    @property
    def name(self):
        return self.model._meta.label

    def detail_url(self, pk):
        return f"{self.url}{pk}/"


_REGISTRY: dict[type, OwnedEndpoint] = {}


def register_owned_endpoint(
    model, url, make, create_payload=None, update_payload=None, actions=ALL_ACTIONS
):
    unknown = set(actions) - ALL_ACTIONS
    if unknown:
        raise ValueError(f"Unknown actions: {sorted(unknown)}")
    if model in _REGISTRY:
        raise ValueError(f"{model._meta.label} is already registered.")
    endpoint = OwnedEndpoint(
        model=model,
        url=url,
        make=make,
        create_payload=dict(create_payload or {}),
        update_payload=dict(update_payload or {}),
        actions=frozenset(actions),
    )
    _REGISTRY[model] = endpoint
    return endpoint


def registered_endpoints():
    return list(_REGISTRY.values())


def concrete_owned_models(models: Iterable[type] | None = None):
    candidates = apps.get_models() if models is None else models
    return [
        model
        for model in candidates
        if issubclass(model, OwnedModel) and not model._meta.abstract
    ]


def assert_all_owned_models_registered(models=None, registry=None):
    registry = _REGISTRY if registry is None else registry
    missing = [m._meta.label for m in concrete_owned_models(models) if m not in registry]
    assert not missing, (
        "Concrete OwnedModel subclasses not registered with the isolation harness "
        f"(tests/isolation.py register_owned_endpoint): {', '.join(missing)}"
    )


def assert_owned_default_managers(models=None):
    wrong = [
        m._meta.label
        for m in concrete_owned_models(models)
        if not isinstance(m._default_manager, OwnedManager)
    ]
    assert not wrong, (
        "Concrete OwnedModel subclasses whose default manager is not OwnedManager: "
        f"{', '.join(wrong)}"
    )


# --- Registered owned endpoints ----------------------------------------------------------

def _register_fixture_endpoints():
    from tests.ownership_fixture.models import Note

    register_owned_endpoint(
        Note,
        "/api/v1/test-notes/",
        make=lambda owner: Note.objects.create(owner=owner, title="private note"),
        create_payload={"title": "new note"},
        update_payload={"title": "changed"},
    )


def _register_lessons_endpoint():
    from lessons.models import Lesson

    register_owned_endpoint(
        Lesson,
        "/api/v1/lessons/",
        make=lambda owner: Lesson.objects.create(owner=owner, title="private lesson"),
        create_payload={"title": "new lesson"},
        actions={"list", "retrieve", "create"},
    )


_register_fixture_endpoints()
_register_lessons_endpoint()
