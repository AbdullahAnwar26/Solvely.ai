"""Staff-only AI diagnostics: GET /api/v1/ai/status/ (Story 3.1)."""
import logging

import pytest

from core import limits

from .test_auth import make_user, signed_in_client
from .test_register import STRONG_PASSWORD, assert_envelope, make_csrf_client

pytestmark = pytest.mark.django_db

URL = "/api/v1/ai/status/"
SECRET_KEY = "AIzaSECRET-diagnostics-key-9876543210"
STAFF = "staff@example.com"
LEARNER = "learner@example.com"


@pytest.fixture
def staff_client():
    make_user(STAFF, is_staff=True)
    return signed_in_client(STAFF, STRONG_PASSWORD)


@pytest.fixture
def learner_client():
    make_user(LEARNER)
    return signed_in_client(LEARNER, STRONG_PASSWORD)


def assert_no_key(response, caplog):
    body = response.content.decode()
    for fragment in (SECRET_KEY, SECRET_KEY[:8], SECRET_KEY[-6:]):
        assert fragment not in body
        assert fragment not in caplog.text


def test_staff_sees_fake_status(staff_client):
    response = staff_client.get(URL)
    assert response.status_code == 200
    assert response.json() == {
        "configured": True,
        "provider": "fake",
        "model": "fake-model",
        "max_attempts": limits.AI_MAX_ATTEMPTS,
        "max_concurrency": limits.AI_MAX_CONCURRENCY,
    }


def test_staff_sees_configured_gemini_without_key(staff_client, settings, caplog):
    caplog.set_level(logging.DEBUG)
    settings.AI_PROVIDER = "gemini"
    settings.GEMINI_API_KEY = SECRET_KEY
    settings.GEMINI_MODEL = "configured-model-id"
    response = staff_client.get(URL)
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is True
    assert body["provider"] == "gemini"
    assert body["model"] == "configured-model-id"
    assert set(body) == {"configured", "provider", "model", "max_attempts", "max_concurrency"}
    assert_no_key(response, caplog)


@pytest.mark.parametrize(
    ("key", "model"), [("", "m"), (SECRET_KEY, ""), ("", "")], ids=["no-key", "no-model", "neither"]
)
def test_staff_sees_unconfigured_gemini(staff_client, settings, key, model, caplog):
    settings.AI_PROVIDER = "gemini"
    settings.GEMINI_API_KEY = key
    settings.GEMINI_MODEL = model
    response = staff_client.get(URL)
    assert response.status_code == 200
    body = response.json()
    assert body["configured"] is False
    assert body["model"] == (model or None)
    assert_no_key(response, caplog)


def test_learner_is_forbidden(learner_client, settings, caplog):
    settings.GEMINI_API_KEY = SECRET_KEY
    response = learner_client.get(URL)
    assert_envelope(response, 403, "permission_denied")
    assert_no_key(response, caplog)


def test_anonymous_is_forbidden(settings, caplog):
    settings.GEMINI_API_KEY = SECRET_KEY
    response = make_csrf_client().get(URL)
    assert_envelope(response, 403, "not_authenticated")
    assert_no_key(response, caplog)


def test_status_is_in_the_openapi_schema(client):
    schema = client.get("/api/v1/schema/", headers={"Accept": "application/json"}).json()
    operation = schema["paths"]["/api/v1/ai/status/"]["get"]
    assert operation["operationId"] == "ai_status"
    assert "200" in operation["responses"] and "403" in operation["responses"]
