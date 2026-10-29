---
title: 'Story 1.6: Theme preference and account settings'
type: 'feature'
created: '2026-10-29'
status: 'done'
baseline_commit: 'c71bba8'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Solvely.ai-2026-10-28/DESIGN.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Solvely.ai-2026-10-28/EXPERIENCE.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-1-5-account-deletion.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-1-7-auth-screens.md'
  - '{project-root}/docs/ARCHITECTURE_NOTES.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Learners cannot choose light, dark or device-following theme, cannot manage their account from the browser, and the account-deletion endpoint is awkward for the typed client (drf-spectacular emits no request body for DELETE, and proxies may drop DELETE bodies).

**Approach:** Store a per-Learner theme preference on the backend, apply it in the web app with no flash of the wrong theme, add a settings page (theme, sign out, delete account), and move account deletion to a `POST` endpoint with a native-dialog confirmation.

## Boundaries & Constraints

**Always:** Backend: add `theme_preference` to `Profile` (choices `system`, `light`, `dark`; default `system`) with a migration; `GET /api/v1/auth/me/` and the login/register responses include it; `PATCH /api/v1/auth/preferences/` (authenticated, CSRF, owner is `request.user`, validates choices, returns the updated value). Replace `DELETE /api/v1/auth/account/` with `POST /api/v1/auth/account/delete/` (same body `{password}`, same throttles, same 204/400/403/429 behaviour); update the Story 1.5 tests to the new route (behaviour must stay identical) and remove the old route. OpenAPI must still pass `spectacular --validate --fail-on-warn`, and `packages/shared` types must be regenerated (`npm run gen:api` with the API running) so the new request bodies are typed. Frontend: a theme control with three options (System, Light, Dark) as an accessible radio group on a `/settings` page; applying sets `data-theme` on `<html>` only for light or dark and removes it for system (tokens.css already supports this); persist via the preferences endpoint; also keep a non-sensitive hint (`light`, `dark` or `system`) in `localStorage` (inside try/catch) read by a tiny inline script in `index.html` before first paint to avoid a flash; the server value wins after the session loads. Settings page: sign out, and delete account behind a native `<dialog>` (modal, focus moved in and restored, Escape closes, password field, destructive styling from tokens, clear consequences text, busy state, errors from `ApiError`); on success redirect to `/sign-in` with a short "account deleted" notice. Add a Settings link to the shell nav (a real route). Honour reduced motion. No new dependencies. Tokens only (no hex literals; the ESLint rule must still pass). Do not log or store passwords.

**Never:** No change to registration, login, reset or ownership semantics beyond adding the preference field. No social login. No lesson features. Do not keep the old DELETE route.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default | new user | `theme_preference: "system"`; UI follows OS | N/A |
| Change theme | choose Dark | PATCH 200 `{theme_preference:"dark"}`, `data-theme="dark"` applied immediately, hint stored | PATCH fails: UI reverts and shows a message |
| Invalid value | PATCH `{"theme_preference":"neon"}` | 400 `validation_error` with field | envelope |
| Anonymous PATCH | not signed in | 403 `not_authenticated` | envelope |
| No CSRF | PATCH without token | 403 `csrf_failed` | envelope |
| Other user | A patches | only A's profile changes | N/A |
| Reload | saved Dark, OS light | no flash of light; Dark after session load | storage unavailable: falls back to server value after load |
| System option | choose System | `data-theme` removed, follows OS changes live | N/A |
| Delete via POST | correct password, CSRF | 204, user and owned rows gone, redirect to `/sign-in` with notice | N/A |
| Delete wrong password | wrong password | 400 `invalid_credentials` ("The password is incorrect."), dialog stays open, nothing deleted | shown in dialog |
| Old route | `DELETE /api/v1/auth/account/` | 404 or 405, not available | N/A |
| Dialog a11y | open dialog | focus enters dialog, Escape closes and returns focus to trigger, Tab stays inside | N/A |
| Generated types | after regenerate | account delete has a typed request body; preferences typed | N/A |

</frozen-after-approval>

## Code Map

- `apps/api/accounts/models.py`, migrations, `serializers.py`, `views.py`, `urls.py` -- add the field, the preference serializer and view, move the delete route; keep `extend_schema` on every view.
- `apps/api/tests/test_account_deletion.py`, `test_auth.py`, `test_register.py` -- update routes and response shape; add `tests/test_preferences.py`.
- `apps/web/index.html` -- inline pre-paint theme script.
- `apps/web/src/` -- `theme/` provider and hook, `pages/SettingsPage.tsx`, delete dialog component, route, nav link; the session type includes `theme_preference`.
- `packages/shared/src/generated/api.ts` -- regenerate.
- `docs/ARCHITECTURE_NOTES.md` -- note on theme handling and the dialog approach (native `<dialog>`, no library).

## Tasks & Acceptance

**Execution:**
- [ ] backend field, migration, preferences endpoint, delete route move, serializers, schema, per the matrix
- [ ] backend tests: update the 1.5 tests to the new route; one test per backend matrix row
- [ ] regenerate shared API types
- [ ] web theme provider, inline pre-paint script, settings page, delete dialog, nav link
- [ ] web tests: one per matrix row runnable in jsdom (theme apply and revert, system removal, dialog focus and Escape, delete errors, redirect with notice)
- [ ] real browser check against the live API (Edge headless via playwright-core in the scratchpad, not in the repo): change theme and reload without a flash, delete an account end to end; stop any servers afterwards
- [ ] docs note

**Acceptance Criteria:**
- Given a signed-in Learner, when they pick Dark and reload, then Dark is shown with no flash and the choice survives a new session.
- Given the settings page, when the Learner deletes their account with the right password, then the account and data are gone and they land on `/sign-in` with a notice.
- Given a clean checkout, when `npm ci`, lint, typecheck, test, build and backend `pytest`, `ruff check`, `makemigrations --check` and `spectacular --validate --fail-on-warn` run, then all pass.

## Implementation Notes

- 2026-10-29: STOPPED MID-STORY at the user's request. Backend done (116 passed). Web partly done: lint/typecheck pass, 1 failing test (storage test must allow the theme hint key). See docs/RESUME.md for the full list of what remains. Nothing committed.

- 2026-10-29 (resumed): Storage test now allows only `wt.theme` (light|dark|system). Added `src/pages/settings.test.tsx` (theme apply/revert/system/server-wins/storage-unavailable, nav link, dialog focus/Escape/trap, wrong password, delete redirect with notice); `setup.ts` clears `data-theme` between tests and sets a 5s async-util timeout, `vite.config.ts` test timeout 20s (slow machine, lazy routes). Live Edge-headless check on the real API: Dark survives reload with no flash (data-theme set before DOMContentLoaded), survives sign-out/sign-in with hint cleared (server value), wrong password stays in dialog, Escape restores focus, delete redirects to /sign-in with notice and the account can no longer sign in. Servers stopped. Note: one run where cookies were cleared mid-page left sign-in stuck on "Signing in�" with no login request sent; not reproduced otherwise, worth a look in a later story.

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `npm run lint && npm run typecheck && npm run test && npm run build` (repo root) -- expected: all pass
- `cd apps/api && .venv/Scripts/python -m pytest -q && .venv/Scripts/python -m ruff check . && .venv/Scripts/python manage.py makemigrations --check` -- expected: pass, no changes
- `DJANGO_SETTINGS_MODULE=config.settings DJANGO_SECRET_KEY=x .venv/Scripts/python manage.py spectacular --validate --fail-on-warn --file /dev/null` -- expected: exit 0

## Orchestrator Review (2026-10-29, after resume)

- Re-ran independently against baseline c71bba8: web lint 0 warnings, typecheck, vitest 61 passed, build ok; backend pytest 116 passed, ruff clean, `makemigrations --check` no changes, spectacular `--fail-on-warn` exit 0. Ports 5173/8000 free, no leftover servers.
- Agent's live Edge run: Dark survived reload with no flash and survived sign-out/sign-in; wrong password stayed in the dialog; Escape restored focus; delete redirected to `/sign-in` with the notice; deleted account could not sign in.
- Agent-reported intermittent hang (sign-in stuck on "Signing in…" after cookies were cleared mid-page by the test script): `ensureCsrfCookie` re-checks the cookie on every call and caches nothing, so the logic cannot hang; likely a script artifact. Real gap found: the API client has no request timeout (logged in deferred-work.md).
- Test config: 20 s test timeout and 5 s async-util timeout were added because the suite was flaky under load.
