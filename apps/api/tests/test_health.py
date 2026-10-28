import pytest


def test_health(client):
    r = client.get("/api/v1/health/")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert r["X-Request-ID"]


@pytest.mark.django_db
def test_ready(client):
    r = client.get("/api/v1/ready/")
    assert r.status_code == 200 and r.json() == {"status": "ready"}


def test_request_id_echoed_when_safe_and_replaced_when_not(client):
    good = client.get("/api/v1/health/", headers={"X-Request-ID": "abc-123"})
    assert good["X-Request-ID"] == "abc-123"
    bad = client.get("/api/v1/health/", headers={"X-Request-ID": "bad id!\t"})
    assert bad["X-Request-ID"] != "bad id!\t"


def test_openapi_schema_served(client):
    assert client.get("/api/v1/schema/").status_code == 200
