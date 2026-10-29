"""Theme preference (Story 1.6)."""
import pytest
from django.conf import settings

from accounts.models import Profile

from .test_auth import ME_URL, make_user, post, signed_in_client
from .test_register import STRONG_PASSWORD, assert_envelope, make_csrf_client

PREFS_URL = "/api/v1/auth/preferences/"
pytestmark = pytest.mark.django_db


def patch(client, data, csrf=True):
    cookie = client.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {"X-CSRFToken": cookie.value} if csrf and cookie else {}
    return client.patch(PREFS_URL, data, content_type="application/json", headers=headers)


def test_default_is_system_on_register_login_and_me():
    client = make_csrf_client()
    response = post(
        client,
        "/api/v1/auth/register/",
        {"email": "new@example.com", "password": STRONG_PASSWORD, "confirm_adult": True},
    )
    assert response.status_code == 201
    assert response.json()["theme_preference"] == "system"
    assert client.get(ME_URL).json()["theme_preference"] == "system"
    make_user("x@example.com")
    login = post(
        make_csrf_client(),
        "/api/v1/auth/login/",
        {"email": "x@example.com", "password": STRONG_PASSWORD},
    )
    assert login.json()["theme_preference"] == "system"


@pytest.mark.parametrize("value", ["dark", "light", "system"])
def test_change_theme(value):
    make_user("a@example.com")
    client = signed_in_client("a@example.com")
    response = patch(client, {"theme_preference": value})
    assert response.status_code == 200
    assert response.json() == {"theme_preference": value}
    assert client.get(ME_URL).json()["theme_preference"] == value
    assert Profile.objects.get(user__email="a@example.com").theme_preference == value


@pytest.mark.parametrize("data", [{"theme_preference": "neon"}, {}], ids=["bad", "missing"])
def test_invalid_value(data):
    make_user("a@example.com")
    client = signed_in_client("a@example.com")
    error = assert_envelope(patch(client, data), 400, "validation_error")
    assert error["fields"]["theme_preference"]
    assert client.get(ME_URL).json()["theme_preference"] == "system"


def test_anonymous_rejected():
    response = patch(make_csrf_client(), {"theme_preference": "dark"})
    assert_envelope(response, 403, "not_authenticated")


def test_no_csrf_rejected():
    make_user("a@example.com")
    client = signed_in_client("a@example.com")
    assert_envelope(patch(client, {"theme_preference": "dark"}, csrf=False), 403, "csrf_failed")
    assert client.get(ME_URL).json()["theme_preference"] == "system"


def test_only_own_profile_changes():
    make_user("a@example.com")
    make_user("b@example.com")
    client_a = signed_in_client("a@example.com")
    assert patch(client_a, {"theme_preference": "dark"}).status_code == 200
    assert Profile.objects.get(user__email="a@example.com").theme_preference == "dark"
    assert Profile.objects.get(user__email="b@example.com").theme_preference == "system"
    # A client-supplied owner is ignored.
    other = Profile.objects.get(user__email="b@example.com").user_id
    patch(client_a, {"theme_preference": "light", "user": other, "user_id": other})
    assert Profile.objects.get(user__email="b@example.com").theme_preference == "system"
