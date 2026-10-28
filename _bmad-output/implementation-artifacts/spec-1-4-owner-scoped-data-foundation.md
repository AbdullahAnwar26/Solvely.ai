---
title: 'Story 1.4: Owner-scoped data foundation'
type: 'feature'
created: '2026-10-28'
status: 'done'
baseline_commit: '7842ccc'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-Solvely.ai-2026-10-27/ARCHITECTURE-SPINE.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Every later feature stores per-learner data, but nothing yet guarantees a learner can only reach their own rows. Ownership must be a shared, enforced foundation (AD-5), not re-implemented per endpoint.

**Approach:** Add an abstract `OwnedModel` with an owner-scoped manager and `for_user()`, DRF building blocks that only ever query through it and set the owner from the request, and a cross-user isolation test harness that new owned endpoints must register with. Prove it end to end with a test-only owned model and viewset.

## Boundaries & Constraints

**Always:** `OwnedModel` is abstract with `owner = ForeignKey(AUTH_USER_MODEL, on_delete=CASCADE, db_index=True, related_name="+")` plus `created_at`/`updated_at`. Its default manager is `OwnedManager` exposing `for_user(user)`; anonymous or `None` users get an empty queryset. DRF base `OwnedModelViewSet` (or mixin) builds its queryset only via `for_user(request.user)`, requires authentication, returns the 404 envelope for foreign or missing ids (never 403), sets `owner=request.user` on create, and treats any client-supplied `owner` as ignored (read-only/not accepted). Test-only model and routes live under `apps/api/tests/` and are enabled only through `config/settings_test.py` (extra INSTALLED_APP and a test ROOT_URLCONF); production settings and urls must not include them.

**Never:** No real product models (Lesson etc.) in this story. No change to Story 1.2/1.3 behaviour. No account deletion endpoint (Story 1.5). No per-object permission classes that return 403 for foreign objects.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Scoped manager | user A and B each own rows | `Model.objects.for_user(A)` returns only A's rows | N/A |
| Anonymous | `for_user(AnonymousUser)` or `None` | empty queryset | N/A |
| List | A authenticated | only A's rows, paginated | anon -> 403 `not_authenticated` envelope |
| Retrieve foreign | A requests B's id | 404 `not_found` envelope, same body as a missing id | envelope |
| Update foreign | A PUT/PATCH B's id | 404, B's row unchanged | envelope |
| Delete foreign | A DELETE B's id | 404, row still exists | envelope |
| Create | A POSTs with `owner` = B's id | 201, row owner is A | N/A |
| Registry guard | a concrete `OwnedModel` subclass not registered with the harness | guard test fails with a message naming the model | N/A |
| Manager guard | concrete `OwnedModel` subclass with a different default manager | guard test fails | N/A |
| User deleted | owner user deleted | owner's rows cascade-deleted, others untouched | N/A |

</frozen-after-approval>

## Code Map

- `apps/api/core/ownership.py` -- new: `OwnedQuerySet`, `OwnedManager`, abstract `OwnedModel`.
- `apps/api/core/api.py` (or `core/viewsets.py`) -- new: `OwnedModelViewSet`/mixin, using the envelope from `core/errors.py` (reuse, do not change).
- `apps/api/tests/ownership_fixture/` -- new test-only app: concrete `Note(OwnedModel)` with a `title`, serializer, viewset, urls.
- `apps/api/config/settings_test.py` -- add the fixture app and test urlconf; keep MD5 hasher.
- `apps/api/tests/isolation.py` -- new: `register_owned_endpoint(...)` registry and the shared parametrised isolation checks.
- `apps/api/tests/test_ownership.py` -- new: matrix tests, guard tests, cascade test.
- `docs/ARCHITECTURE_NOTES.md` -- optional short "how to add an owned model/endpoint" (5-10 lines).

## Tasks & Acceptance

**Execution:**
- [x] `core/ownership.py` -- abstract OwnedModel, OwnedManager, for_user -- shared base for all owned models
- [x] `core/viewsets.py` -- owner-scoped viewset enforcing 404 and owner assignment -- shared base for owned endpoints
- [x] `tests/ownership_fixture/*`, `config/settings_test.py` -- test-only concrete model and routes, test-only wiring
- [x] `tests/isolation.py`, `tests/test_ownership.py` -- registry, shared isolation checks, guard tests, one test per matrix row
- [x] short how-to note in `docs/` for adding owned models

**Acceptance Criteria:**
- Given two users with rows, when either lists, retrieves, updates or deletes via the owned endpoint, then only their own rows are reachable and foreign ids return an envelope 404 identical to a missing id.
- Given a new concrete OwnedModel that is not registered with the isolation harness, when the suite runs, then the guard test fails.
- Given the full suite, when `pytest`, `ruff check` and `makemigrations --check` run, then all pass and production settings do not include the fixture app.

## Implementation Notes

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `cd apps/api && .venv/Scripts/python -m pytest -q` -- expected: all tests pass
- `cd apps/api && .venv/Scripts/python -m ruff check .` -- expected: All checks passed
- `cd apps/api && .venv/Scripts/python manage.py makemigrations --check` -- expected: No changes detected
- `cd apps/api && .venv/Scripts/python manage.py check` -- expected: no issues (production settings, fixture app absent)

## Orchestrator Review (2026-10-28)

- Re-ran independently against baseline 7842ccc: pytest 87 passed, ruff clean, `makemigrations --check` no changes, `manage.py check` clean under production settings (fixture app absent).
- Read `core/ownership.py` and `core/viewsets.py`: queries go only through `for_user`, owner set server-side on create and update, foreign ids give the standard 404 envelope. Agent's mutation test (viewset using `.all()`) failed 5 isolation tests as intended.
- Follow-ups: new owned endpoints register in `tests/isolation.py`; shared checks assume integer ids (use `str()` when UUID ids arrive); OpenAPI validation errors on Story 1.2/1.3 account views and health/ready (see deferred-work.md).
