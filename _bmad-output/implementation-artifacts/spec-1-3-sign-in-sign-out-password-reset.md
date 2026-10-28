---
title: 'Story 1.3: Sign in, sign out, password reset'
type: 'feature'
created: '2026-10-28'
status: 'done'
baseline_commit: 'NO_VCS'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-Solvely.ai-2026-10-27/ARCHITECTURE-SPINE.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-1-2-registration-with-18-confirmation.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Learners can register but cannot sign in again, sign out, or recover a forgotten password.

**Approach:** Add session login, logout, a current-user endpoint and an email-based password reset to the `accounts` app, reusing the Story 1.2 error envelope, CSRF setup and throttling pattern.

## Boundaries & Constraints

**Always:** Session cookie auth; CSRF enforced on login, logout, reset and confirm (anonymous endpoints wrapped with `csrf_protect` as in registration). Email compared case-insensitively. Reset uses Django's `default_token_generator` (single-use, because the token hashes the password and last login) with `PASSWORD_RESET_TIMEOUT` set to 1 hour via a named constant in `core/limits.py`. Reset request always returns the same 202 response whether or not the email exists, with no timing-obvious branch that skips work. Login failure returns one generic error (`invalid_credentials`, HTTP 400) for unknown email and wrong password alike. Login, reset request and reset confirm are throttled per IP (named rates in `core/limits.py`); login is also throttled per submitted email. After a successful password reset all existing sessions of that user are invalid. Passwords validated with the same validators as registration. Never log passwords, tokens or reset URLs at INFO or above.

**Never:** No tokens in responses or browser storage. No email enumeration. No frontend. No social login. No ownership base (Story 1.4). No account deletion (Story 1.5).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Login ok | valid email (any case) + password, CSRF | 200 `{id, email, adult_confirmed_at}`, new session, session key rotated | N/A |
| Login bad | wrong password or unknown email | 400 `invalid_credentials`, identical body both cases | envelope |
| Login inactive | `is_active=False` user | 400 `invalid_credentials` | envelope |
| Login throttled | too many attempts per IP or per email | 429 `throttled`, retryable true | envelope |
| Logout | signed in, CSRF | 204, session deleted server-side; reuse of old cookie is unauthenticated | N/A |
| Logout anon | not signed in | 403 `not_authenticated` envelope | envelope |
| Me | signed in | 200 same shape as login | anon -> 403 `not_authenticated` |
| Reset request | any email, CSRF | 202 `{}` identical for known/unknown; known user gets one email with link `{FRONTEND_BASE_URL}/reset-password?uid=..&token=..` | N/A |
| Reset confirm ok | valid uid+token+strong new password | 200, password changed, token unusable a second time, other sessions invalid | N/A |
| Reset confirm bad | bad/expired/used token or bad uid | 400 `invalid_reset_token` | envelope |
| Reset weak password | valid token, weak password | 400 `validation_error` with `fields.new_password`, token still valid | envelope |
| No CSRF | any POST without token | 403 `csrf_failed` | envelope |

</frozen-after-approval>

## Code Map

- `apps/api/accounts/serializers.py`, `views.py`, `urls.py`, `throttles.py` -- extend (Story 1.2 patterns: `csrf_protect` via `method_decorator`, `RegisteredUserSerializer`, `RegisterRateThrottle`).
- `apps/api/core/limits.py` -- add `LOGIN_RATE`, `LOGIN_EMAIL_RATE`, `RESET_RATE`, `RESET_TIMEOUT_SECONDS`.
- `apps/api/core/errors.py` -- add code mapping only if needed; reuse envelope.
- `apps/api/config/settings.py` -- add throttle rates, `PASSWORD_RESET_TIMEOUT`, `EMAIL_BACKEND` (console when DEBUG, SMTP from env otherwise), `DEFAULT_FROM_EMAIL`, `FRONTEND_BASE_URL` env.
- `apps/api/.env.example` -- document new env vars.
- `apps/api/tests/test_auth.py` -- new; reuse fixtures from `tests/conftest.py` and helpers in `tests/test_register.py`.

## Tasks & Acceptance

**Execution:**
- [x] `core/limits.py`, `config/settings.py`, `.env.example` -- constants, throttle rates, email and reset settings
- [x] `accounts/serializers.py`, `throttles.py`, `views.py`, `urls.py` -- login, logout, me, password-reset request and confirm endpoints under `/api/v1/auth/`
- [x] `tests/test_auth.py` -- one test per matrix row, plus: session fixation (key changes at login), old session cookie rejected after reset, token single use, no enumeration (identical status and body, and exactly one email sent only for a known user), throttle per email, secrets absent from logs

**Acceptance Criteria:**
- Given valid credentials with CSRF, when posted, then the user is signed in with a rotated session and CSRF is required for later unsafe calls.
- Given a reset email for a known user, when its link is confirmed with a strong password, then the password changes, the token is spent, and prior sessions are invalid.
- Given the full suite, when `pytest`, `ruff check` and `makemigrations --check` run, then all pass on PostgreSQL.

## Implementation Notes

- Endpoints: `POST auth/login/`, `POST auth/logout/`, `GET auth/me/`, `POST auth/password-reset/`, `POST auth/password-reset/confirm/`.
- `core/errors.py` gained an `ApiError` base (own code + safe message); `InvalidCredentials` and `InvalidResetToken` subclass it in `accounts/views.py`.
- Rates: `LOGIN_RATE=30/hour`, `LOGIN_EMAIL_RATE=10/hour` (email hashed in the cache key), `RESET_RATE=10/hour` applied separately to request and confirm scopes.
- Reset request validates email format (malformed -> 400 `validation_error`, which does not enumerate); otherwise always 202 `{}`. Token and message are built for unknown emails too; only active users with a usable password are emailed. SMTP failures are logged (type only) and still return 202.
- Prior sessions are invalidated by Django's session auth-hash check after the password change; session rows are not deleted. Confirm does not sign the user in.
- Verified: pytest 66 passed on PostgreSQL, ruff clean, `makemigrations --check` no changes.

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `cd apps/api && .venv/Scripts/python -m pytest -q` -- expected: all tests pass
- `cd apps/api && .venv/Scripts/python -m ruff check .` -- expected: All checks passed
- `cd apps/api && .venv/Scripts/python manage.py makemigrations --check` -- expected: No changes detected

## Orchestrator Review (2026-10-28)

- Re-ran independently: pytest 66 passed, ruff clean, `makemigrations --check` no changes. Read views/throttles for CSRF, session rotation, token single-use, enumeration; no defects found.
- Accepted: malformed email on reset request returns 400 `validation_error` (reveals nothing about accounts). Known limits: reset-send timing difference with real SMTP (needs background send later); mixed-case usernames created outside registration cannot log in; per-IP throttles need the trusted-proxy count in production (Story 7.3).
- Added fast MD5 hasher to `config/settings_test.py` (test runtime 217 s -> 4 s).
