---
title: 'Story 1.2: Registration with 18+ confirmation'
type: 'feature'
created: '2026-10-27'
status: 'done'
baseline_commit: 'NO_VCS'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-Solvely.ai-2026-10-27/ARCHITECTURE-SPINE.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no way to create an account. Gemini's terms require 18+ users, so sign-up must record an 18+ confirmation, and the API has no error envelope or throttling yet.

**Approach:** Add an `accounts` Django app with a registration endpoint that creates a user and profile, stores the 18+ confirmation timestamp, signs the user in with a session cookie, enforces CSRF, and returns errors in the single architecture error envelope.

## Boundaries & Constraints

**Always:** Session cookie auth (HttpOnly, SameSite=Lax, Secure when not DEBUG). CSRF enforced on registration. Email stored lowercase and used as the username; uniqueness case-insensitive. Password checked with Django validators. Errors use `{"error": {"code", "message", "retryable", "request_id", "fields"?}}` with stable string codes. Never log passwords. Registration throttled per IP.

**Never:** No custom user model swap (default `User`, one-to-one `Profile`). No tokens in responses. No email sending, login, logout or reset (Story 1.3). No frontend work (Story 1.1). No ownership base (Story 1.4). Do not reveal anything beyond "email already registered" being a validation error.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | valid email, strong password, `confirm_adult=true` | 201, `{id, email, adult_confirmed_at}`, session cookie set, Profile row with timestamp | N/A |
| Missing 18+ | `confirm_adult` false or absent | 400 code `validation_error`, `fields.confirm_adult`, no user created | envelope |
| Duplicate email | same email in different case | 400 `validation_error`, `fields.email` | envelope |
| Weak password | e.g. `password1` or too short | 400 `validation_error`, `fields.password` with validator messages | envelope |
| Bad email | not an email | 400 `validation_error`, `fields.email` | envelope |
| No CSRF token | POST without valid CSRF | 403 code `csrf_failed` | envelope |
| Throttled | more than limit per hour per IP | 429 code `throttled`, `retryable: true` | envelope |
| Unexpected error | server exception | 500 code `server_error`, generic message, no traceback | envelope, logged with request_id |

</frozen-after-approval>

## Code Map

- `apps/api/config/settings.py` -- add `accounts` app, `AUTH_PASSWORD_VALIDATORS`, DRF `EXCEPTION_HANDLER`, `DEFAULT_AUTHENTICATION_CLASSES` = SessionAuthentication, throttle rate `register`, session cookie settings.
- `apps/api/core/errors.py` -- new: exception handler producing the envelope (maps ValidationError, Throttled, PermissionDenied/CSRF, NotFound, generic) using `request.request_id`.
- `apps/api/core/limits.py` -- new: named constants (e.g. `REGISTER_RATE`, `PASSWORD_MIN_LENGTH`).
- `apps/api/core/middleware.py` -- existing RequestIDMiddleware; reuse, do not change.
- `apps/api/accounts/` -- new app: `models.py` (Profile: OneToOne User, `adult_confirmed_at`), `serializers.py`, `views.py` (CSRF cookie endpoint `GET auth/csrf/`, `POST auth/register/`), `urls.py`, `migrations/`.
- `apps/api/core/urls.py` -- existing health routes; include `accounts.urls` under `/api/v1/` in `config/urls.py`.
- `apps/api/tests/test_register.py` -- new tests.

## Tasks & Acceptance

**Execution:**
- [x] `core/errors.py`, `core/limits.py` -- envelope handler and constants -- shared by every later endpoint
- [x] `accounts/models.py` + migration -- Profile with `adult_confirmed_at` -- stores 18+ confirmation
- [x] `accounts/serializers.py`, `views.py`, `urls.py` -- register + csrf endpoints, `csrf_protect`-wrapped register, login via `django.contrib.auth.login`, scoped throttle -- implements the matrix
- [x] `config/settings.py`, `config/urls.py` -- wire app, validators, handler, throttling, cookies
- [x] `tests/test_register.py` -- one test per matrix row, plus: no password in logs/response, Profile created atomically (rollback leaves no user)

**Acceptance Criteria:**
- Given a valid registration with CSRF token, when posted, then a user and profile exist, the timestamp is stored, and the response sets a session cookie.
- Given any failure row, when posted, then the body matches the envelope and no user is created.
- Given migrations on the clean PostgreSQL test DB, when `pytest` and `ruff check` run, then all pass.

## Implementation Notes

- Implemented by an opus subagent; reviewed and verified by the orchestrator on 2026-10-28 (single reviewer, not BMAD's parallel reviewer step).
- Files: `accounts/` (Profile, RegisterSerializer, RegisterView with csrf_protect, CsrfCookieView, RegisterRateThrottle, migration 0001), `core/errors.py` (envelope handler + CSRF failure view), `core/limits.py`, settings wiring, `tests/test_register.py`, `tests/conftest.py`.
- Verified: pytest 25 passed, ruff clean, `makemigrations --check` no changes; all 8 matrix rows covered by passing tests.
- Known follow-ups: duplicate email is revealed as a validation error (per spec); behind a reverse proxy, set the trusted-proxy count so the per-IP throttle sees real client IPs (Story 7.3).

## Spec Change Log

## Review Triage Log

## Design Notes

Anonymous POSTs bypass DRF's CSRF check (SessionAuthentication only enforces CSRF for authenticated users), so wrap the view with Django's `csrf_protect` and expose `GET /api/v1/auth/csrf/` using `ensure_csrf_cookie`.

## Verification

**Commands:**
- `cd apps/api && .venv/Scripts/python -m pytest -q` -- expected: all tests pass
- `cd apps/api && .venv/Scripts/python -m ruff check .` -- expected: All checks passed
- `cd apps/api && .venv/Scripts/python manage.py makemigrations --check` -- expected: no changes detected
