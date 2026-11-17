"""Board revisions: GET/PUT /api/v1/lessons/{id}/board/ (Story 2.3, AD-4).

Cross-user isolation for the nested endpoint also runs through tests/isolation.py.
"""
import json
import threading
import uuid

import pytest
from django.conf import settings
from django.db import connection

from core import limits
from lessons import board as board_module
from lessons.models import BoardRevision, Lesson

from .test_auth import make_user, signed_in_client
from .test_ownership import send
from .test_register import STRONG_PASSWORD, assert_envelope, make_csrf_client

EMAIL_A = "alice@example.com"
EMAIL_B = "bob@example.com"


def board_url(lesson_id):
    return f"/api/v1/lessons/{lesson_id}/board/"


def element(**over):
    base = {
        "id": "el-1",
        "type": "rectangle",
        "x": 10,
        "y": 20,
        "width": 100,
        "height": 50,
        "angle": 0,
        "version": 3,
        "versionNonce": 123456,
        "isDeleted": False,
        "groupIds": [],
        "boundElements": None,
        "strokeColor": "#1e1e1e",
        "customData": {"origin": "learner"},
    }
    base.update(over)
    return base


def board(elements=None, **over):
    payload = {
        "schema_version": 1,
        "elements": [element()] if elements is None else elements,
        "app_state": {
            "viewBackgroundColor": "transparent",
            "scrollX": 5,
            "scrollY": -7.5,
            "zoom": {"value": 1.25},
        },
    }
    payload.update(over)
    return payload


def save(client, lesson, base, save_id=None, payload=None):
    body = {
        "base_revision": base,
        "save_id": str(save_id or uuid.uuid4()),
        "board": board() if payload is None else payload,
    }
    return send(client, "put", board_url(lesson.pk), body)


def put_raw(client, lesson, raw):
    token = client.cookies[settings.CSRF_COOKIE_NAME].value
    return client.put(
        board_url(lesson.pk), raw, content_type="application/json",
        headers={"X-CSRFToken": token},
    )


@pytest.fixture
def user_a(db):
    return make_user(EMAIL_A)


@pytest.fixture
def user_b(db):
    return make_user(EMAIL_B)


@pytest.fixture
def client_a(user_a):
    return signed_in_client(EMAIL_A, STRONG_PASSWORD)


@pytest.fixture
def lesson(user_a):
    return Lesson.objects.create(owner=user_a)


def rows(lesson):
    return list(BoardRevision.objects.filter(lesson=lesson).order_by("revision"))


# --- Saves and revisions ------------------------------------------------------------------

@pytest.mark.django_db
def test_first_save_creates_revision_1(client_a, lesson, user_a):
    response = save(client_a, lesson, 0)
    assert response.status_code == 200
    assert response.json() == {"revision": 1}
    lesson.refresh_from_db()
    assert lesson.current_revision == 1
    [row] = rows(lesson)
    assert (row.revision, row.owner_id) == (1, user_a.pk)
    assert row.payload == board()


@pytest.mark.django_db
def test_next_save_creates_revision_2(client_a, lesson):
    assert save(client_a, lesson, 0).status_code == 200
    response = save(client_a, lesson, 1, payload=board([element(x=99)]))
    assert response.json() == {"revision": 2}
    assert [r.revision for r in rows(lesson)] == [1, 2]
    lesson.refresh_from_db()
    assert lesson.current_revision == 2


@pytest.mark.django_db
def test_stale_base_is_409_and_writes_nothing(client_a, lesson):
    save(client_a, lesson, 0)
    save(client_a, lesson, 1)
    before = [(r.pk, r.revision, r.payload) for r in rows(lesson)]
    response = save(client_a, lesson, 1, payload=board([element(x=-1)]))
    error = assert_envelope(response, 409, "revision_conflict")
    assert error["current_revision"] == 2
    assert [(r.pk, r.revision, r.payload) for r in rows(lesson)] == before
    lesson.refresh_from_db()
    assert lesson.current_revision == 2


@pytest.mark.django_db
def test_base_ahead_of_current_is_409(client_a, lesson):
    error = assert_envelope(save(client_a, lesson, 5), 409, "revision_conflict")
    assert error["current_revision"] == 0
    assert rows(lesson) == []


@pytest.mark.django_db
def test_retry_with_same_save_id_is_idempotent(client_a, lesson):
    save_id = uuid.uuid4()
    first = save(client_a, lesson, 0, save_id=save_id)
    second = save(client_a, lesson, 0, save_id=save_id)
    assert first.json() == second.json() == {"revision": 1}
    assert len(rows(lesson)) == 1


@pytest.mark.django_db
def test_retry_after_a_later_save_still_returns_its_own_revision(client_a, lesson):
    save_id = uuid.uuid4()
    save(client_a, lesson, 0, save_id=save_id)
    save(client_a, lesson, 1)
    response = save(client_a, lesson, 0, save_id=save_id)
    assert response.status_code == 200
    assert response.json() == {"revision": 1}
    assert len(rows(lesson)) == 2


@pytest.mark.django_db
def test_existing_rows_are_never_updated(client_a, lesson):
    save(client_a, lesson, 0)
    first = rows(lesson)[0]
    save(client_a, lesson, 1, payload=board([element(id="other")]))
    again = BoardRevision.objects.get(pk=first.pk)
    assert (again.payload, again.updated_at) == (first.payload, first.updated_at)


@pytest.mark.django_db
def test_learner_tags_round_trip(client_a, lesson):
    elements = [
        element(id="a", customData={"origin": "learner", "stepId": "s1"}),
        element(id="b", type="text", text="hi", customData={"origin": "ai"}),
        element(id="c", type="freedraw", points=[[0, 0], [1.5, 2.5]], pressures=[0.5, 0.5]),
    ]
    save(client_a, lesson, 0, payload=board(elements))
    body = client_a.get(board_url(lesson.pk)).json()
    assert body["revision"] == 1
    assert body["board"]["elements"] == elements


# --- GET ---------------------------------------------------------------------------------

@pytest.mark.django_db
def test_get_empty_board(client_a, lesson):
    response = client_a.get(board_url(lesson.pk))
    assert response.status_code == 200
    assert response.json() == {"revision": 0, "board": {"schema_version": 1, "elements": []}}


@pytest.mark.django_db
def test_get_latest(client_a, lesson):
    save(client_a, lesson, 0)
    latest = board([element(x=42)])
    save(client_a, lesson, 1, payload=latest)
    assert client_a.get(board_url(lesson.pk)).json() == {"revision": 2, "board": latest}


# --- Ownership and auth --------------------------------------------------------------------

@pytest.mark.django_db
def test_foreign_lesson_is_404_on_get_and_put(client_a, user_b):
    foreign = Lesson.objects.create(owner=user_b)
    assert_envelope(client_a.get(board_url(foreign.pk)), 404, "not_found")
    assert_envelope(save(client_a, foreign, 0), 404, "not_found")
    assert rows(foreign) == []
    foreign.refresh_from_db()
    assert foreign.current_revision == 0


@pytest.mark.django_db
def test_malformed_lesson_id_is_404(client_a):
    assert_envelope(client_a.get("/api/v1/lessons/not-a-uuid/board/"), 404, "not_found")


@pytest.mark.django_db
def test_anonymous_is_403(lesson):
    client = make_csrf_client()
    assert_envelope(client.get(board_url(lesson.pk)), 403, "not_authenticated")
    assert_envelope(save(client, lesson, 0), 403, "not_authenticated")
    assert rows(lesson) == []


@pytest.mark.django_db
def test_put_without_csrf_is_403(client_a, lesson):
    body = {"base_revision": 0, "save_id": str(uuid.uuid4()), "board": board()}
    response = client_a.put(board_url(lesson.pk), body, content_type="application/json")
    assert_envelope(response, 403, "csrf_failed")
    assert rows(lesson) == []


@pytest.mark.django_db
def test_owner_spoof_is_ignored(client_a, lesson, user_a, user_b):
    body = {
        "base_revision": 0,
        "save_id": str(uuid.uuid4()),
        "board": board(),
        "owner": user_b.pk,
        "lesson": str(uuid.uuid4()),
    }
    assert send(client_a, "put", board_url(lesson.pk), body).status_code == 200
    assert [r.owner_id for r in rows(lesson)] == [user_a.pk]


@pytest.mark.django_db
def test_get_and_put_methods_only(client_a, lesson):
    assert_envelope(send(client_a, "post", board_url(lesson.pk), {}), 405, "method_not_allowed")
    assert_envelope(send(client_a, "patch", board_url(lesson.pk), {}), 405, "method_not_allowed")


# --- Validation ----------------------------------------------------------------------------

INVALID_BOARDS = {
    "schema-version-2": board(schema_version=2),
    "schema-version-missing": {"elements": []},
    "schema-version-bool": board(schema_version=True),
    "files-key": board(files={}),
    "unknown-key": board(owner=1),
    "not-an-object": [],
    "elements-not-list": board(elements={}),
    "unknown-type": board([element(type="image")]),
    "embeddable": board([element(type="embeddable")]),
    "element-not-object": board(["x"]),
    "missing-id": board([element(id=None)]),
    "id-too-long": board([element(id="x" * (limits.BOARD_ELEMENT_ID_MAX_LENGTH + 1))]),
    "x-not-number": board([element(x="1")]),
    "x-bool": board([element(x=True)]),
    "x-out-of-bounds": board([element(x=limits.BOARD_COORDINATE_LIMIT + 1)]),
    "width-out-of-bounds": board([element(width=-limits.BOARD_COORDINATE_LIMIT - 1)]),
    "height-missing": board([{k: v for k, v in element().items() if k != "height"}]),
    "bad-origin": board([element(customData={"origin": "teacher"})]),
    "custom-data-not-object": board([element(customData="ai")]),
    "text-too-long": board(
        [element(type="text", text="x" * (limits.BOARD_TEXT_MAX_LENGTH + 1))]
    ),
    "string-too-long": board([element(strokeColor="x" * (limits.BOARD_STRING_MAX_LENGTH + 1))]),
    "too-many-points": board(
        [element(type="freedraw", points=[[0, 0]] * (limits.BOARD_ELEMENT_LIST_MAX + 1))]
    ),
    "too-deep": board([element(customData={"a": {"b": {"c": {"d": {"e": 1}}}}})]),
    "huge-number": board([element(seed=limits.BOARD_NUMBER_ABS_MAX * 10)]),
    "app-state-unknown-key": board(app_state={"theme": "dark"}),
    "app-state-zoom-shape": board(app_state={"zoom": 2}),
    "app-state-zoom-range": board(app_state={"zoom": {"value": limits.BOARD_ZOOM_MAX + 1}}),
    "app-state-scroll-string": board(app_state={"scrollX": "0"}),
    "app-state-background-long": board(
        app_state={"viewBackgroundColor": "x" * (limits.BOARD_BACKGROUND_MAX_LENGTH + 1)}
    ),
}


@pytest.mark.django_db
@pytest.mark.parametrize("payload", INVALID_BOARDS.values(), ids=INVALID_BOARDS.keys())
def test_invalid_board_is_400_and_writes_nothing(client_a, lesson, payload):
    response = save(client_a, lesson, 0, payload=payload)
    assert_envelope(response, 400, "validation_error")
    assert rows(lesson) == []
    lesson.refresh_from_db()
    assert lesson.current_revision == 0


@pytest.mark.django_db
@pytest.mark.parametrize(
    "body",
    [
        {"save_id": str(uuid.uuid4()), "board": board()},
        {"base_revision": -1, "save_id": str(uuid.uuid4()), "board": board()},
        {"base_revision": 0, "save_id": "nope", "board": board()},
        {"base_revision": 0, "save_id": str(uuid.uuid4())},
    ],
    ids=["no-base", "negative-base", "bad-save-id", "no-board"],
)
def test_invalid_envelope_is_400(client_a, lesson, body):
    assert_envelope(send(client_a, "put", board_url(lesson.pk), body), 400, "validation_error")
    assert rows(lesson) == []


@pytest.mark.django_db
@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_numbers_are_rejected(client_a, lesson, constant):
    item = '{"id": "a", "type": "rectangle", "x": X, "y": 0, "width": 1, "height": 1}'
    raw = json.dumps(
        {"base_revision": 0, "save_id": str(uuid.uuid4()),
         "board": {"schema_version": 1, "elements": ["ITEM"]}}
    ).replace('"ITEM"', item.replace("X", constant))
    response = put_raw(client_a, lesson, raw)
    assert response.status_code == 400
    assert response.json()["error"]["code"] in {"parse_error", "validation_error"}
    assert rows(lesson) == []


def test_validator_rejects_non_finite_values_directly():
    from rest_framework.exceptions import ValidationError

    for bad in (float("nan"), float("inf")):
        with pytest.raises(ValidationError):
            board_module.validate_board(board([element(x=bad)]))
        with pytest.raises(ValidationError):
            board_module.validate_board(board([element(angle=bad)]))


def test_validator_accepts_every_allowed_type_and_both_origins():
    elements = [
        element(id=f"e{i}", type=kind, customData={"origin": origin})
        for i, kind in enumerate(sorted(limits.BOARD_ELEMENT_TYPES))
        for origin in sorted(limits.BOARD_ORIGINS)
    ]
    payload = board(elements)
    assert board_module.validate_board(payload) is payload
    assert board_module.validate_board({"schema_version": 1, "elements": []})


@pytest.mark.django_db
def test_too_many_elements_is_400(client_a, lesson):
    elements = [element(id=f"e{i}") for i in range(limits.BOARD_MAX_ELEMENTS + 1)]
    assert_envelope(save(client_a, lesson, 0, payload=board(elements)), 400, "validation_error")
    assert rows(lesson) == []


@pytest.mark.django_db
def test_max_elements_is_accepted(client_a, lesson):
    elements = [element(id=f"e{i}") for i in range(limits.BOARD_MAX_ELEMENTS)]
    assert save(client_a, lesson, 0, payload=board(elements)).status_code == 200


@pytest.mark.django_db
def test_body_over_limit_is_413(client_a, lesson):
    text = "x" * limits.BOARD_TEXT_MAX_LENGTH
    count = limits.BOARD_MAX_BODY_BYTES // limits.BOARD_TEXT_MAX_LENGTH + 2
    elements = [element(id=f"t{i}", type="text", text=text) for i in range(count)]
    body = {"base_revision": 0, "save_id": str(uuid.uuid4()), "board": board(elements)}
    raw = json.dumps(body)
    assert len(raw.encode()) > limits.BOARD_MAX_BODY_BYTES
    assert_envelope(put_raw(client_a, lesson, raw), 413, "payload_too_large")
    assert rows(lesson) == []


def test_limits_constants():
    assert limits.BOARD_MAX_ELEMENTS == 5000
    assert limits.BOARD_MAX_BODY_BYTES == 2 * 1024 * 1024
    assert limits.BOARD_REVISIONS_KEPT == 50
    assert limits.BOARD_SCHEMA_VERSION == 1
    assert limits.BOARD_ELEMENT_ID_MAX_LENGTH == 64
    assert limits.BOARD_ELEMENT_TYPES == {
        "rectangle", "diamond", "ellipse", "arrow", "line", "freedraw", "text", "frame"
    }
    assert limits.BOARD_ORIGINS == {"learner", "ai"}
    # Django's own body cap must not be below ours, or large valid saves would fail first.
    assert settings.DATA_UPLOAD_MAX_MEMORY_SIZE >= limits.BOARD_MAX_BODY_BYTES


# --- Pruning and throttling ----------------------------------------------------------------

@pytest.mark.django_db
def test_pruning_keeps_latest_revisions(client_a, lesson, monkeypatch):
    from lessons.throttles import BoardSaveRateThrottle

    monkeypatch.setattr(BoardSaveRateThrottle, "THROTTLE_RATES", {"board_save": "1000/min"})
    total = limits.BOARD_REVISIONS_KEPT + 2
    for base in range(total):
        payload = board([element(x=base)])
        assert save(client_a, lesson, base, payload=payload).json() == {"revision": base + 1}
    kept = [r.revision for r in rows(lesson)]
    assert kept == list(range(total - limits.BOARD_REVISIONS_KEPT + 1, total + 1))
    assert len(kept) == limits.BOARD_REVISIONS_KEPT
    body = client_a.get(board_url(lesson.pk)).json()
    assert body["revision"] == total
    assert body["board"]["elements"][0]["x"] == total - 1


@pytest.mark.django_db
def test_pruning_only_touches_this_lesson(client_a, lesson, user_a, monkeypatch):
    from lessons.throttles import BoardSaveRateThrottle

    monkeypatch.setattr(BoardSaveRateThrottle, "THROTTLE_RATES", {"board_save": "1000/min"})
    other = Lesson.objects.create(owner=user_a)
    save(client_a, other, 0)
    for base in range(limits.BOARD_REVISIONS_KEPT + 1):
        save(client_a, lesson, base)
    assert len(rows(other)) == 1


@pytest.mark.django_db
def test_saves_are_throttled_per_user(client_a, lesson, monkeypatch):
    from lessons.throttles import BoardSaveRateThrottle

    assert limits.BOARD_SAVE_RATE == "120/min"
    monkeypatch.setattr(BoardSaveRateThrottle, "THROTTLE_RATES", {"board_save": "2/min"})
    assert save(client_a, lesson, 0).status_code == 200
    assert save(client_a, lesson, 1).status_code == 200
    assert_envelope(save(client_a, lesson, 2), 429, "throttled", retryable=True)
    # Reading the Board is not limited by the save rate.
    assert client_a.get(board_url(lesson.pk)).status_code == 200


# --- Concurrency (real PostgreSQL transactions) --------------------------------------------

def _concurrent_puts(lesson, bodies, monkeypatch):
    """Send the PUTs from separate threads (separate DB connections) so they overlap.

    Validation runs while the Lesson row is locked; a short sleep inside it keeps the first
    request holding the lock while the second arrives.
    """
    import time

    real_validate = board_module.validate_board

    def slow_validate(payload):
        time.sleep(0.3)
        return real_validate(payload)

    monkeypatch.setattr("lessons.views.validate_board", slow_validate)
    barrier = threading.Barrier(len(bodies))
    results = [None] * len(bodies)

    def worker(index, body):
        try:
            client = signed_in_client(EMAIL_A, STRONG_PASSWORD)
            barrier.wait(timeout=10)
            results[index] = send(client, "put", board_url(lesson.pk), body)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker, args=(i, b)) for i, b in enumerate(bodies)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


@pytest.mark.django_db(transaction=True)
def test_concurrent_saves_on_same_base_one_wins(user_a, monkeypatch):
    lesson = Lesson.objects.create(owner=user_a)
    bodies = [
        {"base_revision": 0, "save_id": str(uuid.uuid4()), "board": board([element(x=i)])}
        for i in range(2)
    ]
    results = _concurrent_puts(lesson, bodies, monkeypatch)
    statuses = sorted(r.status_code for r in results)
    assert statuses == [200, 409], [r.content for r in results]
    loser = next(r for r in results if r.status_code == 409)
    assert loser.json()["error"]["current_revision"] == 1
    winner = results.index(next(r for r in results if r.status_code == 200))
    [row] = rows(lesson)
    assert row.revision == 1
    assert row.payload == bodies[winner]["board"]
    lesson.refresh_from_db()
    assert lesson.current_revision == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_retries_with_same_save_id_create_one_revision(user_a, monkeypatch):
    lesson = Lesson.objects.create(owner=user_a)
    body = {"base_revision": 0, "save_id": str(uuid.uuid4()), "board": board()}
    results = _concurrent_puts(lesson, [body, dict(body)], monkeypatch)
    assert [r.status_code for r in results] == [200, 200], [r.content for r in results]
    assert [r.json() for r in results] == [{"revision": 1}, {"revision": 1}]
    assert len(rows(lesson)) == 1
