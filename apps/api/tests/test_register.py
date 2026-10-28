import logging
from datetime import datetime

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client

from accounts.models import Profile
from core import limits

REGISTER_URL = "/api/v1/auth/register/"
CSRF_URL = "/api/v1/auth/csrf/"
STRONG_PASSWORD = "violet-harbor-tunnel-42"

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def csrf_client():
    return make_csrf_client()


def make_csrf_client():
    client = Client(enforce_csrf_checks=True)
    assert client.get(CSRF_URL).status_code == 204
    return client


def register(client, payload, csrf_token=None, **extra):
    # Read the token fresh each time: login() rotates it.
    cookie = client.cookies.get(settings.CSRF_COOKIE_NAME)
    token = csrf_token or (cookie.value if cookie else None)
    headers = {"X-CSRFToken": token} if token else {}
    return client.post(
        REGISTER_URL, payload, content_type="application/json", headers=headers, **extra
    )


def payload(**overrides):
    data = {"email": "Learner@Example.com", "password": STRONG_PASSWORD, "confirm_adult": True}
    data.update(overrides)
    return {k: v for k, v in data.items() if v is not ...}


def assert_envelope(response, status, code, retryable=False):
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    error = body["error"]
    assert error["code"] == code
    assert error["retryable"] is retryable
    assert isinstance(error["message"], str) and error["message"]
    assert error["request_id"] == response["X-Request-ID"]
    assert "Traceback" not in response.content.decode()
    return error


# Happy path ---------------------------------------------------------------

def test_happy_path_creates_user_profile_and_session(csrf_client):
    response = register(csrf_client, payload())

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email", "adult_confirmed_at"}
    assert body["email"] == "learner@example.com"

    user = User.objects.get(pk=body["id"])
    assert user.username == user.email == "learner@example.com"
    assert user.check_password(STRONG_PASSWORD)
    profile = Profile.objects.get(user=user)
    assert profile.adult_confirmed_at is not None
    assert datetime.fromisoformat(body["adult_confirmed_at"]) == profile.adult_confirmed_at

    session_cookie = response.cookies[settings.SESSION_COOKIE_NAME]
    assert session_cookie.value
    assert session_cookie["httponly"]
    assert session_cookie["samesite"] == "Lax"
    # The session is live: the user is signed in on the next request.
    assert int(csrf_client.session["_auth_user_id"]) == user.pk
    assert "token" not in response.content.decode().lower()


# Failure rows -------------------------------------------------------------

@pytest.mark.parametrize("confirm_adult", [False, ...])
def test_missing_adult_confirmation_rejected(csrf_client, confirm_adult):
    response = register(csrf_client, payload(confirm_adult=confirm_adult))
    error = assert_envelope(response, 400, "validation_error")
    assert "confirm_adult" in error["fields"]
    assert not User.objects.exists()


def test_duplicate_email_case_insensitive(csrf_client):
    assert register(csrf_client, payload()).status_code == 201
    response = register(make_csrf_client(), payload(email="LEARNER@example.COM"))
    error = assert_envelope(response, 400, "validation_error")
    assert error["fields"]["email"] == ["This email is already registered."]
    assert User.objects.count() == 1


@pytest.mark.parametrize("weak", ["password1", "short1!", "1234567890123"])
def test_weak_password_rejected_with_validator_messages(csrf_client, weak):
    response = register(csrf_client, payload(password=weak))
    error = assert_envelope(response, 400, "validation_error")
    messages = error["fields"]["password"]
    assert messages and all(isinstance(m, str) for m in messages)
    assert not User.objects.exists()


def test_password_too_short_mentions_min_length(csrf_client):
    response = register(csrf_client, payload(password="Zq9#kd"))
    error = assert_envelope(response, 400, "validation_error")
    assert any(str(limits.PASSWORD_MIN_LENGTH) in m for m in error["fields"]["password"])


def test_password_similar_to_email_rejected(csrf_client):
    response = register(
        csrf_client, payload(email="harborview@example.com", password="harborview")
    )
    error = assert_envelope(response, 400, "validation_error")
    assert "password" in error["fields"]


@pytest.mark.parametrize("email", ["not-an-email", "", "a@", ...])
def test_bad_email_rejected(csrf_client, email):
    response = register(csrf_client, payload(email=email))
    error = assert_envelope(response, 400, "validation_error")
    assert "email" in error["fields"]
    assert not User.objects.exists()


def test_no_csrf_token_rejected():
    client = Client(enforce_csrf_checks=True)
    response = client.post(REGISTER_URL, payload(), content_type="application/json")
    assert_envelope(response, 403, "csrf_failed")
    assert not User.objects.exists()


def test_wrong_csrf_token_rejected(csrf_client):
    response = register(csrf_client, payload(), csrf_token="x" * 32)
    assert_envelope(response, 403, "csrf_failed")
    assert not User.objects.exists()


def test_throttled_per_ip(csrf_client):
    allowed = int(limits.REGISTER_RATE.split("/")[0])
    for _ in range(allowed):
        assert register(csrf_client, {}).status_code == 400
    response = register(csrf_client, payload())
    assert_envelope(response, 429, "throttled", retryable=True)
    assert response["Retry-After"]
    assert not User.objects.exists()


def test_throttle_not_bypassed_by_spoofed_forwarded_for(csrf_client):
    allowed = int(limits.REGISTER_RATE.split("/")[0])
    for i in range(allowed):
        register(csrf_client, {}, HTTP_X_FORWARDED_FOR=f"10.0.0.{i}")
    response = register(csrf_client, payload(), HTTP_X_FORWARDED_FOR="10.9.9.9")
    assert response.status_code == 429


def test_unexpected_error_is_generic_and_logged(csrf_client, monkeypatch, caplog):
    def boom(*args, **kwargs):
        raise RuntimeError("database exploded")

    monkeypatch.setattr("accounts.views.RegisterSerializer.save", boom)
    with caplog.at_level(logging.ERROR, logger="core.errors"):
        response = register(csrf_client, payload())

    error = assert_envelope(response, 500, "server_error")
    assert "exploded" not in response.content.decode()
    assert any(error["request_id"] in r.getMessage() for r in caplog.records)


# Cross-cutting ------------------------------------------------------------

def test_profile_creation_is_atomic(csrf_client, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("profile insert failed")

    monkeypatch.setattr(Profile.objects, "create", fail)
    response = register(csrf_client, payload())
    assert_envelope(response, 500, "server_error")
    assert not User.objects.exists()
    assert not Profile.objects.exists()


def test_password_never_in_logs_or_responses(csrf_client, monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)
    responses = [
        register(csrf_client, payload()),
        register(csrf_client, payload()),  # duplicate
        register(csrf_client, payload(email="x@example.com", confirm_adult=False)),
    ]
    monkeypatch.setattr(Profile.objects, "create", lambda **kw: 1 / 0)
    responses.append(register(csrf_client, payload(email="y@example.com")))

    for response in responses:
        assert STRONG_PASSWORD not in response.content.decode()
    assert STRONG_PASSWORD not in caplog.text
    for record in caplog.records:
        assert STRONG_PASSWORD not in repr(record.args)


def test_csrf_endpoint_sets_cookie_without_body():
    response = Client().get(CSRF_URL)
    assert response.status_code == 204
    assert response.cookies[settings.CSRF_COOKIE_NAME].value
    assert not response.content
