---
title: 'Story 1.5: Account deletion'
type: 'feature'
created: '2026-10-28'
status: 'done'
baseline_commit: 'a34d744'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-Solvely.ai-2026-10-27/ARCHITECTURE-SPINE.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-1-3-sign-in-sign-out-password-reset.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-1-4-owner-scoped-data-foundation.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A learner cannot delete their account or data, which the PRD (FR-18) requires for privacy and control.

**Approach:** Add an authenticated, password-confirmed endpoint that deletes the user and everything they own in one transaction, ends the session, and a guard that keeps later owned models deletable.

## Boundaries & Constraints

**Always:** `DELETE /api/v1/auth/account/` with JSON `{"password": "..."}`; requires an authenticated session and CSRF (`csrf_protect` as in earlier views). Password is verified with `check_password`; a wrong password returns 400 `invalid_credentials` (same envelope code as login) and deletes nothing. Deletion runs in one `transaction.atomic()`; it relies on `on_delete=CASCADE` from the user to `Profile` and every `OwnedModel`. Success returns 204 and the caller's session is ended (logout/flush), so the old cookie is unauthenticated afterwards. Throttled per IP and per user with named rates in `core/limits.py`. Never log the password. Do not reveal other users' data.

**Never:** No soft delete, no grace period, no admin tooling, no email notification, no frontend. No change to registration/login/reset/ownership behaviour. Do not add product models.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Delete ok | signed in, correct password, CSRF | 204; user, profile and all owned rows gone; old session cookie now unauthenticated | N/A |
| Wrong password | signed in, wrong password | 400 `invalid_credentials`; nothing deleted | envelope |
| Missing password | signed in, no password field | 400 `validation_error` with `fields.password` | envelope |
| Anonymous | not signed in | 403 `not_authenticated` | envelope |
| No CSRF | signed in, no token | 403 `csrf_failed` | envelope |
| Others untouched | users A and B both own rows; A deletes | B's user, profile and rows unchanged | N/A |
| Atomic | failure injected mid-delete | nothing deleted, 500 envelope | envelope |
| Throttled | too many attempts | 429 `throttled`, retryable true | envelope |
| FK guard | any model with a FK to the user model using an on_delete other than CASCADE | guard test fails naming the model and field | N/A |
| No orphans | after delete | no row in any model with a FK to the user references that user id | N/A |

</frozen-after-approval>

## Code Map

- `apps/api/accounts/views.py`, `serializers.py`, `urls.py`, `throttles.py` -- extend following Story 1.3 patterns (`csrf_protect` via `method_decorator`, `InvalidCredentials`, throttle base classes).
- `apps/api/core/limits.py` -- add `ACCOUNT_DELETE_RATE`.
- `apps/api/config/settings.py` -- add throttle scope.
- `apps/api/tests/test_account_deletion.py` -- new; reuse fixtures/helpers from `tests/test_auth.py` and `tests/ownership_fixture` (`Note`) for owned rows.
- `docs/ARCHITECTURE_NOTES.md` -- add one line: owned models are deleted by cascade; new FKs to the user must be CASCADE.

## Tasks & Acceptance

**Execution:**
- [x] `core/limits.py`, `config/settings.py` -- named rate and throttle scope
- [x] `accounts/serializers.py`, `throttles.py`, `views.py`, `urls.py` -- delete-account endpoint
- [x] `tests/test_account_deletion.py` -- one test per matrix row, using introspection (`User._meta.related_objects`) for the no-orphans and FK guard checks
- [x] `docs/ARCHITECTURE_NOTES.md` -- one-line rule

**Acceptance Criteria:**
- Given a signed-in learner with owned rows, when they delete with the right password and CSRF, then every row owned by them is gone in one transaction and others are untouched.
- Given a model added later with a non-cascading FK to the user, when the suite runs, then the FK guard test fails.
- Given the full suite, when `pytest`, `ruff check` and `makemigrations --check` run, then all pass on PostgreSQL.

## Implementation Notes

- Endpoint `DELETE auth/account/` (`AccountDeleteView`). Wrong password raises `IncorrectPassword`, a subclass of `InvalidCredentials` (same `invalid_credentials` code, message "The password is incorrect.").
- Rate `ACCOUNT_DELETE_RATE=10/hour`, applied to scopes `account_delete` (per IP) and `account_delete_user` (per user id). Throttles run after auth/permission, so anonymous calls get 403 before any throttle.
- Introspection uses `User._meta.get_fields(include_hidden=True)` filtered to `ManyToOneRel`, not `related_objects`: `related_objects` hides relations with `related_name="+"`, which is exactly what `OwnedModel.owner` uses. A sanity test asserts the guard sees `accounts.Profile.user` and `ownership_fixture.Note.owner`.
- Atomic test injects a `post_delete` failure on `Note`. `Model.delete()` is itself atomic, so this test would also pass without the view's explicit `transaction.atomic()`; the wrapper is kept for intent and for future multi-step deletion.
- Verified: pytest 105 passed on PostgreSQL, ruff clean, `makemigrations --check` no changes, `manage.py check` clean. Mutation checks: skipping the password check fails 3 tests; removing logout fails the session test.

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `cd apps/api && .venv/Scripts/python -m pytest -q` -- expected: all tests pass
- `cd apps/api && .venv/Scripts/python -m ruff check .` -- expected: All checks passed
- `cd apps/api && .venv/Scripts/python manage.py makemigrations --check` -- expected: No changes detected

## Orchestrator Review (2026-10-28)

- Re-ran independently against baseline a34d744: pytest 105 passed, ruff clean, `makemigrations --check` no changes.
- Read `AccountDeleteView`: password verified before delete, delete atomic, session ended, 204. Confirmed the agent's deviation is right: `User._meta.related_objects` omits `related_name="+"` relations such as `OwnedModel.owner`, so guards use `get_fields(include_hidden=True)`.
- Known limits: the view's own `transaction.atomic()` is redundant with Django's delete transaction (kept for intent); other sessions' rows remain until cleared (they are unauthenticated at once); per-IP throttles need the trusted-proxy count in production (Story 7.3).
