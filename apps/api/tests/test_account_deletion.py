"""Account deletion (Story 1.5, FR-18)."""
import logging

import pytest
from django.conf import settings
from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.db import SessionStore
from django.db import models
from django.db.models import ManyToOneRel
from django.db.models.signals import post_delete
from django.test import Client
from django.test.utils import isolate_apps

from accounts.models import Profile
from core import limits
from core.ownership import OwnedModel
from tests.ownership_fixture.models import Note

from .test_auth import ME_URL, make_user, signed_in_client
from .test_register import STRONG_PASSWORD, assert_envelope, make_csrf_client

ACCOUNT_URL = "/api/v1/auth/account/delete/"
OLD_ACCOUNT_URL = "/api/v1/auth/account/"
EMAIL_A = "alice@example.com"
EMAIL_B = "bob@example.com"
WRONG_PASSWORD = "not-my-password-123"

pytestmark = pytest.mark.django_db
User = get_user_model()


# --- Helpers ------------------------------------------------------------------------------

def delete_account(client, data=None, csrf=True, **extra):
    cookie = client.cookies.get(settings.CSRF_COOKIE_NAME)
    headers = {"X-CSRFToken": cookie.value} if csrf and cookie else {}
    if data is None:
        data = {"password": STRONG_PASSWORD}
    return client.post(
        ACCOUNT_URL, data, content_type="application/json", headers=headers, **extra
    )


def user_foreign_keys():
    """Every FK / one-to-one field in the project that points at the user model.

    Uses include_hidden=True: OwnedModel's owner has related_name="+", which
    `User._meta.related_objects` leaves out. Also covers auto-created M2M through tables.
    """
    return [
        rel.field
        for rel in User._meta.get_fields(include_hidden=True)
        if isinstance(rel, ManyToOneRel)  # includes OneToOneRel
    ]


def assert_user_fks_cascade(fields=None):
    fields = user_foreign_keys() if fields is None else fields
    offenders = [
        f"{field.model._meta.label}.{field.name} "
        f"(on_delete={field.remote_field.on_delete.__name__})"
        for field in fields
        if field.remote_field.on_delete is not models.CASCADE
    ]
    assert not offenders, (
        "Foreign keys to the user model must use on_delete=CASCADE so account deletion "
        f"removes every owned row: {', '.join(offenders)}"
    )


def rows_referencing(user_id):
    """{"app.Model.field": count} of rows still pointing at user_id, across all user FKs."""
    found = {}
    for field in user_foreign_keys():
        count = field.model._base_manager.filter(**{field.attname: user_id}).count()
        if count:
            found[f"{field.model._meta.label}.{field.name}"] = count
    return found


@pytest.fixture
def user_a():
    return make_user(EMAIL_A)


@pytest.fixture
def user_b():
    return make_user(EMAIL_B)


@pytest.fixture
def client_a(user_a):
    return signed_in_client(EMAIL_A, STRONG_PASSWORD)


def give_rows(user, notes=2):
    for i in range(notes):
        Note.objects.create(owner=user, title=f"{user.email}-{i}")
    group, _ = Group.objects.get_or_create(name="learners")
    user.groups.add(group)
    LogEntry.objects.create(
        user=user,
        content_type=ContentType.objects.get_for_model(User),
        object_id=str(user.pk),
        object_repr=str(user),
        action_flag=ADDITION,
    )


def assert_account_intact(user, notes=2):
    assert User.objects.filter(pk=user.pk).exists()
    assert Profile.objects.filter(user_id=user.pk).exists()
    assert Note.objects.for_user(user).count() == notes


# --- Matrix -------------------------------------------------------------------------------

def test_delete_ok_removes_everything_and_ends_session(client_a, user_a):
    give_rows(user_a)
    user_id = user_a.pk
    assert rows_referencing(user_id)  # sanity: notes, profile, group link, log entry
    old_key = client_a.cookies[settings.SESSION_COOKIE_NAME].value
    other_device = signed_in_client(EMAIL_A, STRONG_PASSWORD)

    response = delete_account(client_a)

    assert response.status_code == 204
    assert response.content == b""
    assert not User.objects.filter(pk=user_id).exists()
    assert not Profile.objects.filter(user_id=user_id).exists()
    assert not Note.objects.filter(owner_id=user_id).exists()
    assert not SessionStore().exists(old_key)
    replay = Client()
    replay.cookies[settings.SESSION_COOKIE_NAME] = old_key
    assert_envelope(replay.get(ME_URL), 403, "not_authenticated")
    assert_envelope(client_a.get(ME_URL), 403, "not_authenticated")
    assert_envelope(other_device.get(ME_URL), 403, "not_authenticated")


def test_old_delete_route_is_gone(client_a, user_a):
    give_rows(user_a)
    cookie = client_a.cookies[settings.CSRF_COOKIE_NAME].value
    response = client_a.delete(
        OLD_ACCOUNT_URL,
        {"password": STRONG_PASSWORD},
        content_type="application/json",
        headers={"X-CSRFToken": cookie},
    )
    assert response.status_code in (404, 405)
    assert_account_intact(user_a)


def test_delete_route_rejects_other_methods(client_a, user_a):
    assert client_a.get(ACCOUNT_URL).status_code == 405
    assert_account_intact(user_a, notes=0)


def test_wrong_password_deletes_nothing(client_a, user_a):
    give_rows(user_a)
    response = delete_account(client_a, {"password": WRONG_PASSWORD})
    error = assert_envelope(response, 400, "invalid_credentials")
    assert "fields" not in error
    assert_account_intact(user_a)
    assert client_a.get(ME_URL).status_code == 200


@pytest.mark.parametrize("data", [{}, {"password": ""}], ids=["absent", "blank"])
def test_missing_password_is_validation_error(client_a, user_a, data):
    give_rows(user_a)
    error = assert_envelope(delete_account(client_a, data), 400, "validation_error")
    assert error["fields"]["password"]
    assert_account_intact(user_a)


def test_anonymous_rejected(user_a):
    give_rows(user_a)
    response = delete_account(make_csrf_client())
    assert_envelope(response, 403, "not_authenticated")
    assert_account_intact(user_a)


def test_no_csrf_rejected(client_a, user_a):
    give_rows(user_a)
    response = delete_account(client_a, csrf=False)
    assert_envelope(response, 403, "csrf_failed")
    assert_account_intact(user_a)
    assert client_a.get(ME_URL).status_code == 200


def test_bad_csrf_token_rejected(client_a, user_a):
    response = client_a.post(
        ACCOUNT_URL,
        {"password": STRONG_PASSWORD},
        content_type="application/json",
        headers={"X-CSRFToken": "x" * 32},
    )
    assert_envelope(response, 403, "csrf_failed")
    assert_account_intact(user_a, notes=0)


def test_other_users_untouched(client_a, user_a, user_b):
    give_rows(user_a)
    give_rows(user_b, notes=3)
    client_b = signed_in_client(EMAIL_B, STRONG_PASSWORD)
    b_before = rows_referencing(user_b.pk)

    assert delete_account(client_a).status_code == 204

    assert_account_intact(user_b, notes=3)
    assert rows_referencing(user_b.pk) == b_before
    assert Group.objects.filter(name="learners").exists()
    assert client_b.get(ME_URL).status_code == 200


def test_atomic_failure_mid_delete_rolls_back(client_a, user_a, caplog):
    give_rows(user_a)
    before = rows_referencing(user_a.pk)

    def explode(sender, instance, **kwargs):
        raise RuntimeError("injected failure after notes were deleted")

    post_delete.connect(explode, sender=Note, dispatch_uid="test-account-delete-explode")
    try:
        with caplog.at_level(logging.ERROR):
            response = delete_account(client_a)
    finally:
        post_delete.disconnect(sender=Note, dispatch_uid="test-account-delete-explode")

    assert_envelope(response, 500, "server_error")
    assert_account_intact(user_a)
    assert rows_referencing(user_a.pk) == before
    assert client_a.get(ME_URL).status_code == 200


def test_throttled_per_user_across_ips(client_a, user_a):
    allowed = int(limits.ACCOUNT_DELETE_RATE.split("/")[0])
    for i in range(allowed):
        response = delete_account(
            client_a, {"password": WRONG_PASSWORD}, REMOTE_ADDR=f"10.0.0.{i}"
        )
        assert response.status_code == 400
    # Right password from a fresh IP: still throttled for this user.
    response = delete_account(client_a, REMOTE_ADDR="10.0.1.1")
    assert_envelope(response, 429, "throttled", retryable=True)
    assert response["Retry-After"]
    assert_account_intact(user_a, notes=0)


def test_throttled_per_ip_across_users():
    allowed = int(limits.ACCOUNT_DELETE_RATE.split("/")[0])
    for i in range(allowed):
        email = f"user{i}@example.com"
        make_user(email)
        client = signed_in_client(email, STRONG_PASSWORD)
        assert delete_account(client, {"password": WRONG_PASSWORD}).status_code == 400
    last = make_user("last@example.com")
    client = signed_in_client("last@example.com", STRONG_PASSWORD)
    assert_envelope(delete_account(client), 429, "throttled", retryable=True)
    assert_account_intact(last, notes=0)


def test_fk_guard_passes_for_project_models():
    fields = user_foreign_keys()
    labels = {f"{f.model._meta.label}.{f.name}" for f in fields}
    # Sanity: the guard actually sees the profile and hidden OwnedModel owner FKs.
    assert {"accounts.Profile.user", "ownership_fixture.Note.owner"} <= labels
    assert_user_fks_cascade()


@isolate_apps("tests.ownership_fixture")
@pytest.mark.parametrize(
    "on_delete", [models.PROTECT, models.SET_NULL, models.DO_NOTHING],
    ids=["protect", "set_null", "do_nothing"],
)
def test_fk_guard_fails_for_non_cascading_fk(on_delete):
    class Dangling(models.Model):
        learner = models.ForeignKey(
            settings.AUTH_USER_MODEL, on_delete=on_delete, null=True, related_name="+"
        )

        class Meta:
            app_label = "ownership_fixture"

    with pytest.raises(AssertionError, match=r"ownership_fixture\.Dangling\.learner"):
        assert_user_fks_cascade(fields=[Dangling._meta.get_field("learner")])


@isolate_apps("tests.ownership_fixture")
def test_fk_guard_accepts_cascading_owned_model():
    class Fine(OwnedModel):
        class Meta:
            app_label = "ownership_fixture"

    assert_user_fks_cascade(fields=[Fine._meta.get_field("owner")])


def test_no_orphans_after_delete(client_a, user_a, user_b):
    give_rows(user_a)
    give_rows(user_b)
    user_id = user_a.pk

    assert delete_account(client_a).status_code == 204

    assert rows_referencing(user_id) == {}
    assert rows_referencing(user_b.pk)


def test_password_absent_from_logs_and_responses(client_a, user_a, caplog):
    caplog.set_level(logging.DEBUG)
    responses = [
        delete_account(client_a, {"password": WRONG_PASSWORD}),
        delete_account(client_a),
    ]
    for response in responses:
        body = response.content.decode()
        assert STRONG_PASSWORD not in body and WRONG_PASSWORD not in body
    for secret in (STRONG_PASSWORD, WRONG_PASSWORD):
        assert secret not in caplog.text
        for record in caplog.records:
            assert secret not in repr(record.args)
