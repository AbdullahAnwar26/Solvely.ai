"""Owner-scoped data foundation (Story 1.4, AD-5).

The isolation checks run against every endpoint registered in tests/isolation.py.
"""
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import models
from django.test.utils import isolate_apps

from core.ownership import OwnedManager, OwnedModel
from tests.isolation import (
    assert_all_owned_models_registered,
    assert_owned_default_managers,
    registered_endpoints,
)
from tests.ownership_fixture.models import Note

from .test_auth import make_user, signed_in_client
from .test_register import STRONG_PASSWORD, assert_envelope, make_csrf_client

pytestmark = pytest.mark.django_db

EMAIL_A = "alice@example.com"
EMAIL_B = "bob@example.com"
ENDPOINTS = registered_endpoints()


def endpoint_params():
    return pytest.mark.parametrize("endpoint", ENDPOINTS, ids=[e.name for e in ENDPOINTS])


@pytest.fixture
def user_a():
    return make_user(EMAIL_A)


@pytest.fixture
def user_b():
    return make_user(EMAIL_B)


@pytest.fixture
def client_a(user_a):
    return signed_in_client(EMAIL_A, STRONG_PASSWORD)


def send(client, method, url, data=None):
    cookie = client.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {"X-CSRFToken": cookie.value} if cookie else {}
    return getattr(client, method)(
        url, data or {}, content_type="application/json", headers=headers
    )


def without_request_id(response):
    error = dict(response.json()["error"])
    error.pop("request_id")
    return error


def missing_pk(endpoint, owner):
    """A primary key of the right type that no longer exists."""
    row = endpoint.make(owner)
    pk = row.pk
    row.delete()
    return pk


# --- Manager ------------------------------------------------------------------------------

def test_for_user_returns_only_own_rows(user_a, user_b):
    a_rows = {Note.objects.create(owner=user_a, title="a").pk for _ in range(2)}
    Note.objects.create(owner=user_b, title="b")
    assert set(Note.objects.for_user(user_a).values_list("pk", flat=True)) == a_rows
    assert Note.objects.for_user(user_b).count() == 1


@pytest.mark.parametrize("anon", [AnonymousUser(), None], ids=["anonymous", "none"])
def test_for_user_anonymous_or_none_is_empty(user_a, anon):
    Note.objects.create(owner=user_a, title="a")
    assert list(Note.objects.for_user(anon)) == []


def test_owned_model_shape():
    assert OwnedModel._meta.abstract
    owner = Note._meta.get_field("owner")
    assert owner.related_model is get_user_model()
    assert owner.remote_field.on_delete is models.CASCADE
    assert owner.db_index
    assert owner.remote_field.related_name == "+"
    assert {"created_at", "updated_at"} <= {f.name for f in Note._meta.get_fields()}
    assert isinstance(Note._default_manager, OwnedManager)


def test_deleting_user_cascades_only_their_rows(user_a, user_b):
    Note.objects.create(owner=user_a, title="a")
    b_note = Note.objects.create(owner=user_b, title="b")
    user_a.delete()
    assert list(Note.objects.values_list("pk", flat=True)) == [b_note.pk]


# --- Shared isolation checks over every registered endpoint ------------------------------

@endpoint_params()
def test_list_anonymous_rejected(endpoint):
    assert_envelope(make_csrf_client().get(endpoint.url), 403, "not_authenticated")


@endpoint_params()
def test_list_returns_only_own_rows_paginated(endpoint, client_a, user_a, user_b):
    own = {endpoint.make(user_a).pk for _ in range(2)}
    endpoint.make(user_b)
    response = client_a.get(endpoint.url)
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert {row["id"] for row in body["results"]} == own
    assert all("owner" not in row for row in body["results"])


@endpoint_params()
def test_retrieve_own_row(endpoint, client_a, user_a):
    row = endpoint.make(user_a)
    response = client_a.get(endpoint.detail_url(row.pk))
    assert response.status_code == 200
    assert response.json()["id"] == row.pk


@endpoint_params()
def test_retrieve_foreign_is_404_same_as_missing(endpoint, client_a, user_b):
    foreign = endpoint.make(user_b)
    foreign_response = client_a.get(endpoint.detail_url(foreign.pk))
    missing_response = client_a.get(endpoint.detail_url(missing_pk(endpoint, user_b)))
    assert_envelope(foreign_response, 404, "not_found")
    assert_envelope(missing_response, 404, "not_found")
    assert without_request_id(foreign_response) == without_request_id(missing_response)


@endpoint_params()
@pytest.mark.parametrize("method", ["put", "patch"])
def test_update_foreign_is_404_and_unchanged(endpoint, method, client_a, user_b):
    foreign = endpoint.make(user_b)
    before = endpoint.model.objects.filter(pk=foreign.pk).values().get()
    response = send(client_a, method, endpoint.detail_url(foreign.pk), endpoint.update_payload)
    assert_envelope(response, 404, "not_found")
    assert endpoint.model.objects.filter(pk=foreign.pk).values().get() == before


@endpoint_params()
def test_update_missing_is_404(endpoint, client_a, user_b):
    pk = missing_pk(endpoint, user_b)
    response = send(client_a, "patch", endpoint.detail_url(pk), endpoint.update_payload)
    assert_envelope(response, 404, "not_found")


@endpoint_params()
def test_delete_foreign_is_404_and_row_kept(endpoint, client_a, user_b):
    foreign = endpoint.make(user_b)
    response = send(client_a, "delete", endpoint.detail_url(foreign.pk))
    assert_envelope(response, 404, "not_found")
    assert endpoint.model.objects.filter(pk=foreign.pk).exists()


@endpoint_params()
def test_delete_own_row(endpoint, client_a, user_a):
    row = endpoint.make(user_a)
    response = send(client_a, "delete", endpoint.detail_url(row.pk))
    assert response.status_code == 204
    assert not endpoint.model.objects.filter(pk=row.pk).exists()


@endpoint_params()
def test_create_ignores_client_owner(endpoint, client_a, user_a, user_b):
    payload = {**endpoint.create_payload, "owner": user_b.pk}
    response = send(client_a, "post", endpoint.url, payload)
    assert response.status_code == 201
    row = endpoint.model.objects.get(pk=response.json()["id"])
    assert row.owner_id == user_a.pk


@endpoint_params()
def test_update_cannot_change_owner(endpoint, client_a, user_a, user_b):
    row = endpoint.make(user_a)
    payload = {**endpoint.update_payload, "owner": user_b.pk}
    response = send(client_a, "patch", endpoint.detail_url(row.pk), payload)
    assert response.status_code == 200
    row.refresh_from_db()
    assert row.owner_id == user_a.pk


# --- Guards -------------------------------------------------------------------------------

def test_every_owned_model_is_registered():
    assert_all_owned_models_registered()


def test_every_owned_model_uses_owned_manager():
    assert_owned_default_managers()


def test_fixture_endpoint_is_registered():
    assert Note in {e.model for e in ENDPOINTS}


@isolate_apps("tests.ownership_fixture")
def test_registry_guard_fails_for_unregistered_model():
    class Unregistered(OwnedModel):
        class Meta:
            app_label = "ownership_fixture"

    with pytest.raises(AssertionError, match="ownership_fixture.Unregistered"):
        assert_all_owned_models_registered(models=[Unregistered])


@isolate_apps("tests.ownership_fixture")
def test_manager_guard_fails_for_plain_default_manager():
    class PlainManaged(OwnedModel):
        objects = models.Manager()

        class Meta:
            app_label = "ownership_fixture"

    with pytest.raises(AssertionError, match="ownership_fixture.PlainManaged"):
        assert_owned_default_managers(models=[PlainManaged])
