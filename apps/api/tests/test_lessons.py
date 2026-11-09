"""Lesson create, retrieve and list (Story 2.1). Shared isolation checks live in test_ownership."""
import uuid

import pytest

from core import limits
from lessons.models import Lesson

from .test_auth import make_user, signed_in_client
from .test_ownership import send
from .test_register import STRONG_PASSWORD, assert_envelope, make_csrf_client

pytestmark = pytest.mark.django_db

URL = "/api/v1/lessons/"
EMAIL_A = "alice@example.com"
EMAIL_B = "bob@example.com"


@pytest.fixture
def user_a():
    return make_user(EMAIL_A)


@pytest.fixture
def user_b():
    return make_user(EMAIL_B)


@pytest.fixture
def client_a(user_a):
    return signed_in_client(EMAIL_A, STRONG_PASSWORD)


def test_create_default(client_a, user_a):
    response = send(client_a, "post", URL, {})
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "title", "current_revision", "created_at", "updated_at"}
    assert uuid.UUID(body["id"])
    assert body["title"] == "Untitled lesson"
    assert body["current_revision"] == 0
    assert Lesson.objects.get(pk=body["id"]).owner_id == user_a.pk


def test_create_titled(client_a):
    response = send(client_a, "post", URL, {"title": "Big-O"})
    assert response.status_code == 201
    assert response.json()["title"] == "Big-O"


@pytest.mark.parametrize(
    "title",
    ["x" * (limits.LESSON_TITLE_MAX_LENGTH + 1), "   ", ""],
    ids=["too-long", "blank-only", "empty"],
)
def test_create_invalid_title(client_a, title):
    response = send(client_a, "post", URL, {"title": title})
    error = assert_envelope(response, 400, "validation_error")
    assert "title" in error["fields"]


def test_create_title_at_limit(client_a):
    response = send(client_a, "post", URL, {"title": "x" * limits.LESSON_TITLE_MAX_LENGTH})
    assert response.status_code == 201


def test_create_ignores_client_owner_and_revision(client_a, user_a, user_b):
    response = send(
        client_a, "post", URL, {"owner": user_b.pk, "current_revision": 9, "id": str(uuid.uuid4())}
    )
    assert response.status_code == 201
    lesson = Lesson.objects.get(pk=response.json()["id"])
    assert lesson.owner_id == user_a.pk
    assert lesson.current_revision == 0


def test_anonymous_rejected():
    client = make_csrf_client()
    assert_envelope(client.get(URL), 403, "not_authenticated")
    assert_envelope(send(client, "post", URL, {}), 403, "not_authenticated")


def test_create_without_csrf_rejected(client_a):
    response = client_a.post(URL, {}, content_type="application/json")
    assert_envelope(response, 403, "csrf_failed")
    assert not Lesson.objects.exists()


def test_retrieve_own(client_a, user_a):
    lesson = Lesson.objects.create(owner=user_a, title="Mine")
    response = client_a.get(f"{URL}{lesson.pk}/")
    assert response.status_code == 200
    assert response.json()["title"] == "Mine"


def test_retrieve_foreign_and_missing_have_same_body(client_a, user_b):
    foreign = Lesson.objects.create(owner=user_b)
    a = client_a.get(f"{URL}{foreign.pk}/")
    b = client_a.get(f"{URL}{uuid.uuid4()}/")
    assert_envelope(a, 404, "not_found")
    assert_envelope(b, 404, "not_found")
    strip = lambda r: {k: v for k, v in r.json()["error"].items() if k != "request_id"}  # noqa: E731
    assert strip(a) == strip(b)


def test_retrieve_malformed_id_is_404(client_a):
    assert_envelope(client_a.get(f"{URL}not-a-uuid/"), 404, "not_found")


def test_list_only_own_newest_first_paginated(client_a, user_a, user_b):
    older = Lesson.objects.create(owner=user_a, title="older")
    newer = Lesson.objects.create(owner=user_a, title="newer")
    Lesson.objects.create(owner=user_b, title="theirs")
    body = client_a.get(URL).json()
    assert body["count"] == 2
    assert [r["id"] for r in body["results"]] == [str(newer.pk), str(older.pk)]
    assert {"next", "previous", "results"} <= set(body)


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_other_methods_not_allowed(client_a, user_a, method):
    lesson = Lesson.objects.create(owner=user_a)
    response = send(client_a, method, f"{URL}{lesson.pk}/", {"title": "x"})
    assert_envelope(response, 405, "method_not_allowed")
    assert Lesson.objects.filter(pk=lesson.pk).exists()


def test_create_is_throttled_per_user(client_a, monkeypatch):
    from rest_framework.throttling import SimpleRateThrottle

    from lessons.throttles import LessonCreateRateThrottle

    assert limits.LESSON_CREATE_RATE == "60/hour"
    monkeypatch.setitem(SimpleRateThrottle.THROTTLE_RATES, "lesson_create", "2/hour")
    monkeypatch.setattr(LessonCreateRateThrottle, "THROTTLE_RATES", {"lesson_create": "2/hour"})
    assert send(client_a, "post", URL, {}).status_code == 201
    assert send(client_a, "post", URL, {}).status_code == 201
    assert_envelope(send(client_a, "post", URL, {}), 429, "throttled", retryable=True)
    # Reading is not throttled by the create limit.
    assert client_a.get(URL).status_code == 200
