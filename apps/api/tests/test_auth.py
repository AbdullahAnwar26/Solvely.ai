import logging
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sessions.backends.db import SessionStore
from django.core import mail
from django.test import Client
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.models import Profile
from core import limits

from .test_register import STRONG_PASSWORD, assert_envelope, make_csrf_client

LOGIN_URL = "/api/v1/auth/login/"
LOGOUT_URL = "/api/v1/auth/logout/"
ME_URL = "/api/v1/auth/me/"
RESET_URL = "/api/v1/auth/password-reset/"
CONFIRM_URL = "/api/v1/auth/password-reset/confirm/"
EMAIL = "learner@example.com"
NEW_PASSWORD = "copper-meadow-lantern-77"

pytestmark = pytest.mark.django_db
User = get_user_model()


@pytest.fixture
def user():
    return make_user(EMAIL)


@pytest.fixture
def client():
    return make_csrf_client()


def make_user(email, password=STRONG_PASSWORD, **extra):
    created = User.objects.create_user(username=email, email=email, password=password, **extra)
    Profile.objects.create(user=created, adult_confirmed_at=timezone.now())
    return created


def post(client, url, data=None, **extra):
    # Read the token fresh each time: login() rotates it.
    cookie = client.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {"X-CSRFToken": cookie.value} if cookie else {}
    return client.post(
        url, data or {}, content_type="application/json", headers=headers, **extra
    )


def login(client, email=EMAIL, password=STRONG_PASSWORD, **extra):
    return post(client, LOGIN_URL, {"email": email, "password": password}, **extra)


def signed_in_client(email=EMAIL, password=STRONG_PASSWORD):
    client = make_csrf_client()
    assert login(client, email, password).status_code == 200
    return client


def request_reset(client, email=EMAIL):
    return post(client, RESET_URL, {"email": email})


def reset_params(message):
    link = next(line for line in message.body.splitlines() if "reset-password?" in line)
    parts = urlsplit(link.strip())
    query = parse_qs(parts.query)
    return link.strip(), parts, query["uid"][0], query["token"][0]


def emailed_reset(client, email=EMAIL):
    mail.outbox.clear()
    assert request_reset(client, email).status_code == 202
    assert len(mail.outbox) == 1
    _, _, uid, token = reset_params(mail.outbox[0])
    return uid, token


def confirm(client, uid, token, new_password=NEW_PASSWORD):
    return post(client, CONFIRM_URL, {"uid": uid, "token": token, "new_password": new_password})


def without_request_id(response):
    body = response.json()
    body["error"].pop("request_id")
    return body


# Login --------------------------------------------------------------------

@pytest.mark.parametrize("email", [EMAIL, "LEARNER@Example.COM", "  Learner@example.com "])
def test_login_ok_any_case(client, user, email):
    response = login(client, email)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"id", "email", "adult_confirmed_at", "theme_preference"}
    assert body["id"] == user.pk
    assert body["email"] == EMAIL
    assert datetime.fromisoformat(body["adult_confirmed_at"]) == user.profile.adult_confirmed_at
    assert int(client.session["_auth_user_id"]) == user.pk
    session_cookie = response.cookies[settings.SESSION_COOKIE_NAME]
    assert session_cookie["httponly"]
    assert "token" not in response.content.decode().lower()


def test_login_rotates_session_key(client, user):
    session = client.session
    session["pre_login"] = True
    session.save()
    old_key = session.session_key
    assert client.cookies[settings.SESSION_COOKIE_NAME].value == old_key

    assert login(client).status_code == 200

    new_key = client.cookies[settings.SESSION_COOKIE_NAME].value
    assert new_key and new_key != old_key
    assert not SessionStore().exists(old_key)


def test_csrf_required_for_unsafe_calls_after_login(client, user):
    assert login(client).status_code == 200
    response = client.post(LOGOUT_URL, content_type="application/json")
    assert_envelope(response, 403, "csrf_failed")
    assert client.get(ME_URL).status_code == 200


def test_login_bad_password_and_unknown_email_identical(client, user):
    wrong = login(client, password="not-the-password-123")
    unknown = login(make_csrf_client(), email="nobody@example.com")

    assert_envelope(wrong, 400, "invalid_credentials")
    assert_envelope(unknown, 400, "invalid_credentials")
    assert without_request_id(wrong) == without_request_id(unknown)
    assert "fields" not in wrong.json()["error"]
    assert "_auth_user_id" not in client.session


def test_login_inactive_user_rejected(client):
    make_user(EMAIL, is_active=False)
    response = login(client)
    assert_envelope(response, 400, "invalid_credentials")
    assert "_auth_user_id" not in client.session


def test_login_missing_fields_is_validation_error(client):
    error = assert_envelope(post(client, LOGIN_URL, {}), 400, "validation_error")
    assert set(error["fields"]) == {"email", "password"}


def test_login_throttled_per_ip(client, user):
    allowed = int(limits.LOGIN_RATE.split("/")[0])
    for i in range(allowed):
        # Distinct emails so the per-email limit is not what trips.
        assert login(client, email=f"user{i}@example.com").status_code == 400
    response = login(client)
    assert_envelope(response, 429, "throttled", retryable=True)
    assert response["Retry-After"]


def test_login_throttled_per_email_across_ips(client, user):
    allowed = int(limits.LOGIN_EMAIL_RATE.split("/")[0])
    for i in range(allowed):
        response = login(client, password="wrong-password-xyz", REMOTE_ADDR=f"10.0.0.{i}")
        assert response.status_code == 400
    # Correct password, new IP, different case: still throttled for this email.
    response = login(client, email=EMAIL.upper(), REMOTE_ADDR="10.0.1.1")
    assert_envelope(response, 429, "throttled", retryable=True)
    # Another email from a fresh IP is unaffected.
    make_user("other@example.com")
    assert login(client, email="other@example.com", REMOTE_ADDR="10.0.2.1").status_code == 200


# Logout and me ------------------------------------------------------------

def test_logout_deletes_session_and_old_cookie_is_unauthenticated(user):
    client = signed_in_client()
    old_key = client.cookies[settings.SESSION_COOKIE_NAME].value

    response = post(client, LOGOUT_URL)

    assert response.status_code == 204
    assert not SessionStore().exists(old_key)
    replay = Client()
    replay.cookies[settings.SESSION_COOKIE_NAME] = old_key
    assert_envelope(replay.get(ME_URL), 403, "not_authenticated")


def test_logout_anonymous_rejected(client):
    assert_envelope(post(client, LOGOUT_URL), 403, "not_authenticated")


def test_me_signed_in(user):
    client = signed_in_client()
    response = client.get(ME_URL)
    assert response.status_code == 200
    assert response.json() == login(make_csrf_client()).json()


def test_me_anonymous_rejected():
    assert_envelope(Client().get(ME_URL), 403, "not_authenticated")


# Password reset request ---------------------------------------------------

def test_reset_request_known_and_unknown_identical(client, user):
    known = request_reset(client, "Learner@Example.com")
    assert len(mail.outbox) == 1
    unknown = request_reset(make_csrf_client(), "nobody@example.com")
    assert len(mail.outbox) == 1

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json() == {}
    assert known.content == unknown.content

    message = mail.outbox[0]
    assert message.to == [EMAIL]
    link, parts, uid, token = reset_params(message)
    assert link.startswith(f"{settings.FRONTEND_BASE_URL}/reset-password?")
    assert parts.path == "/reset-password"
    assert uid and token
    assert token not in known.content.decode()


@pytest.mark.parametrize("state", ["inactive", "unusable_password"])
def test_reset_request_skips_accounts_that_cannot_sign_in(client, state):
    created = make_user(EMAIL, is_active=state != "inactive")
    if state == "unusable_password":
        created.set_unusable_password()
        created.save()
    response = request_reset(client)
    assert response.status_code == 202
    assert response.json() == {}
    assert mail.outbox == []


def test_reset_request_send_failure_still_202(client, user, monkeypatch, caplog):
    def broken_send(self, *args, **kwargs):
        raise ConnectionRefusedError("smtp down")

    monkeypatch.setattr("django.core.mail.EmailMessage.send", broken_send)
    with caplog.at_level(logging.ERROR, logger="accounts.views"):
        response = request_reset(client)
    assert response.status_code == 202
    assert response.json() == {}
    assert "reset-password" not in caplog.text


def test_reset_request_throttled_per_ip(client):
    allowed = int(limits.RESET_RATE.split("/")[0])
    for i in range(allowed):
        assert request_reset(client, f"user{i}@example.com").status_code == 202
    assert_envelope(request_reset(client), 429, "throttled", retryable=True)


def test_reset_timeout_setting_matches_limit():
    assert settings.PASSWORD_RESET_TIMEOUT == limits.RESET_TIMEOUT_SECONDS == 3600


# Password reset confirm ---------------------------------------------------

def test_reset_confirm_ok_changes_password_and_spends_token(client, user):
    other_session = signed_in_client()
    assert other_session.get(ME_URL).status_code == 200
    uid, token = emailed_reset(client)

    response = confirm(client, uid, token)

    assert response.status_code == 200
    assert response.json() == {}
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    # Single use.
    assert_envelope(confirm(client, uid, token, "another-strong-pass-91"), 400,
                    "invalid_reset_token")
    # Sessions from before the reset are signed out.
    assert_envelope(other_session.get(ME_URL), 403, "not_authenticated")
    # Old password fails, new one works.
    assert_envelope(login(make_csrf_client()), 400, "invalid_credentials")
    assert login(make_csrf_client(), password=NEW_PASSWORD).status_code == 200


def test_reset_confirm_bad_token(client, user):
    uid, token = emailed_reset(client)
    response = confirm(client, uid, token[:-2] + "zz")
    assert_envelope(response, 400, "invalid_reset_token")
    user.refresh_from_db()
    assert user.check_password(STRONG_PASSWORD)


@pytest.mark.parametrize("uid", ["", "!!!", "OTk5OTk5", "YWJj"])
def test_reset_confirm_bad_uid(client, user, uid):
    _, token = emailed_reset(client)
    response = confirm(client, uid, token)
    code = "validation_error" if uid == "" else "invalid_reset_token"
    assert_envelope(response, 400, code)


def test_reset_confirm_token_for_other_user_rejected(client, user):
    other = make_user("other@example.com")
    _, token = emailed_reset(client)
    other_uid = urlsafe_base64_encode(force_bytes(other.pk))
    assert_envelope(confirm(client, other_uid, token), 400, "invalid_reset_token")


def test_reset_confirm_expired_token(client, user, monkeypatch):
    uid, token = emailed_reset(client)
    later = datetime.now() + timedelta(seconds=limits.RESET_TIMEOUT_SECONDS + 1)
    monkeypatch.setattr(default_token_generator, "_now", lambda: later)
    assert_envelope(confirm(client, uid, token), 400, "invalid_reset_token")


def test_reset_confirm_token_valid_just_before_expiry(client, user, monkeypatch):
    uid, token = emailed_reset(client)
    later = datetime.now() + timedelta(seconds=limits.RESET_TIMEOUT_SECONDS - 60)
    monkeypatch.setattr(default_token_generator, "_now", lambda: later)
    assert confirm(client, uid, token).status_code == 200


def test_reset_confirm_token_spent_after_login(client, user):
    uid, token = emailed_reset(client)
    # A later sign-in changes last_login, which also invalidates outstanding tokens.
    assert login(make_csrf_client()).status_code == 200
    assert_envelope(confirm(client, uid, token), 400, "invalid_reset_token")


@pytest.mark.parametrize("weak", ["password1", "short1!", "1234567890123", "learner@example"])
def test_reset_confirm_weak_password_keeps_token_valid(client, user, weak):
    uid, token = emailed_reset(client)

    response = confirm(client, uid, token, weak)

    error = assert_envelope(response, 400, "validation_error")
    assert error["fields"]["new_password"]
    user.refresh_from_db()
    assert user.check_password(STRONG_PASSWORD)
    assert confirm(client, uid, token).status_code == 200


def test_reset_confirm_throttled_per_ip(client):
    allowed = int(limits.RESET_RATE.split("/")[0])
    for _ in range(allowed):
        assert confirm(client, "YWJj", "x-y").status_code == 400
    assert_envelope(confirm(client, "YWJj", "x-y"), 429, "throttled", retryable=True)


# CSRF ---------------------------------------------------------------------

@pytest.mark.parametrize("url", [LOGIN_URL, LOGOUT_URL, RESET_URL, CONFIRM_URL])
def test_no_csrf_rejected(url, user):
    client = Client(enforce_csrf_checks=True)
    response = client.post(
        url,
        {"email": EMAIL, "password": STRONG_PASSWORD, "uid": "x", "token": "y",
         "new_password": NEW_PASSWORD},
        content_type="application/json",
    )
    assert_envelope(response, 403, "csrf_failed")
    assert mail.outbox == []
    assert "_auth_user_id" not in client.session


def test_logout_without_csrf_keeps_session(user):
    client = signed_in_client()
    response = client.post(LOGOUT_URL, headers={"X-CSRFToken": "x" * 32})
    assert_envelope(response, 403, "csrf_failed")
    assert client.get(ME_URL).status_code == 200


# Secrets ------------------------------------------------------------------

def test_secrets_absent_from_logs_and_responses(client, user, caplog):
    caplog.set_level(logging.DEBUG)
    responses = [
        login(client, password="wrong-password-xyz"),
        login(client),
        post(client, LOGOUT_URL),
    ]
    uid, token = emailed_reset(client)
    link = reset_params(mail.outbox[0])[0]
    responses += [
        request_reset(client, "nobody@example.com"),
        confirm(client, uid, token, "password1"),
        confirm(client, uid, token),
        confirm(client, uid, token),
    ]

    secrets = [STRONG_PASSWORD, "wrong-password-xyz", NEW_PASSWORD, token, link]
    for response in responses:
        body = response.content.decode()
        assert not any(secret in body for secret in secrets)
    for secret in secrets:
        assert secret not in caplog.text
        for record in caplog.records:
            assert secret not in repr(record.args)
