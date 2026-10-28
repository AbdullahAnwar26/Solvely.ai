---
title: 'Story 1.7: Sign-up, sign-in and password reset screens'
type: 'feature'
created: '2026-10-29'
status: 'done'
baseline_commit: 'f86114c'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Solvely.ai-2026-10-28/DESIGN.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Solvely.ai-2026-10-28/EXPERIENCE.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-1-1-web-app-shell-and-api-client.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-1-3-sign-in-sign-out-password-reset.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The accounts API (register, login, logout, me, password reset) exists but a Learner cannot use it from the browser.

**Approach:** Add auth screens and a session layer to `apps/web` using the Story 1.1 client and shell, following the UX contract, with no tokens in browser storage.

## Boundaries & Constraints

**Always:** Routes `/sign-up`, `/sign-in`, `/forgot-password`, `/reset-password` (reads `uid` and `token` query params). Session state comes only from `GET /api/v1/auth/me/` on app load (403 means signed out); call `GET /api/v1/auth/csrf/` before the first unsafe request so the CSRF cookie exists. Unauthenticated users hitting any app route are redirected to `/sign-in` (remember the target, return after sign-in); signed-in users visiting auth routes are redirected home. Sign-up fields: email, password, 18+ confirmation checkbox (unchecked by default, required); show per-field server errors from `ApiError.fields` and the password rules message from the server; on success the user is already signed in. Sign-in shows ONE generic failure message for `invalid_credentials`; `throttled` shows a retry-later notice; network errors a retry message. Forgot-password always shows the same confirmation after a 202, regardless of email. Reset form (new password) maps `invalid_reset_token` to a clear "link invalid or expired" state with a link to request a new one, and server password errors to the field. Sign out is a real control in the shell (sidebar/drawer) calling `POST /api/v1/auth/logout/`, then clearing session state. The shell shows the signed-in email. Forms follow EXPERIENCE.md: visible labels, `autocomplete` attributes (`email`, `new-password`, `current-password`), error summary that takes focus on failed submit, `aria-describedby`/`aria-invalid` on fields, submit button disabled with visible busy state while pending, Enter submits, keyboard operable, tokens only (no hex literals; the ESLint rule must still pass). No third-party UI library added. No secrets, tokens, passwords or emails written to `localStorage`/`sessionStorage`/logs.

**Never:** No social-login buttons. No account-deletion UI or theme toggle (Story 1.6). No new backend endpoints or behaviour changes. No fake or mocked data in the shipped code. Do not weaken the 18+ requirement client-side or skip server validation.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Sign-up ok | valid email, strong password, 18+ checked | signed in, redirected to `/`, shell shows email | N/A |
| Sign-up 18+ unchecked | submit without box | field error on the checkbox, no request sent or server error mapped | summary focuses |
| Sign-up duplicate/weak/bad email | server `validation_error` with fields | messages shown under the right fields and in the summary | focus to summary |
| Sign-in ok | valid credentials | signed in, returns to remembered route or `/` | N/A |
| Sign-in bad | `invalid_credentials` | single generic message, password cleared, email kept | no field hints |
| Throttled | 429 `throttled` | notice "Too many attempts, try again later", form re-enabled | N/A |
| Network down | fetch rejects | "Could not reach the server. Check your connection and retry." | button re-enabled |
| Session bootstrap | `/auth/me/` 403 | treated as signed out, no error shown | N/A |
| Guard | signed out visits `/` | redirected to `/sign-in`, returns to `/` after sign-in | N/A |
| Auth route while signed in | visit `/sign-in` | redirected `/` | N/A |
| Forgot password | any valid-format email | same confirmation message always | invalid format -> field error |
| Reset ok | valid uid+token+strong password | success message, link to sign in | N/A |
| Reset bad link | `invalid_reset_token` | invalid/expired state with link to `/forgot-password` | N/A |
| Reset weak password | server `validation_error` | message under `new_password`, link remains usable | N/A |
| Sign out | click Sign out | logout call, session cleared, redirect `/sign-in` | failure -> message, stays signed in |
| No storage use | any flow | nothing auth-related written to browser storage | test asserts |

</frozen-after-approval>

## Code Map

- `apps/web/src/api/client.ts` -- existing typed client with CSRF and `ApiError`; reuse, extend only if needed.
- `apps/web/src/app/routes.tsx`, `AppShell.tsx` -- existing router and shell; add guarded routes, email display, sign-out control.
- `apps/web/src/auth/` -- new: session context/provider, route guard, forms, pages, tests.
- `apps/web/src/styles/` -- use existing tokens; add form styles using tokens.
- `packages/shared/src/generated/api.ts` -- generated types; regenerate with `npm run gen:api` only if the API schema changed (it should not).
- `docs/ARCHITECTURE_NOTES.md` -- add a short note on the auth/session approach.

## Tasks & Acceptance

**Execution:**
- [ ] `src/auth/` session provider + guard -- bootstrap via `/auth/me/`, CSRF priming, redirect logic
- [ ] sign-up, sign-in, forgot-password, reset-password pages -- per matrix, accessible forms
- [ ] shell integration -- email display and working Sign out
- [ ] tests (Vitest + Testing Library, fetch mocked) -- one per matrix row, plus focus-to-summary and no-storage assertions
- [ ] real end-to-end run against the live API (DEBUG settings, console email backend): register, sign out, sign in, request reset (read link from API console output), set new password, sign in with it; record result in Implementation Notes; stop any servers you start
- [ ] `docs/ARCHITECTURE_NOTES.md` short note

**Acceptance Criteria:**
- Given a clean checkout, when `npm ci`, `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build` run from the repo root, then all pass and backend `pytest` still reports 105 passed.
- Given the live stack, when a Learner registers, signs out, signs in and completes a password reset in the browser, then each step works and the final sign-in uses the new password.
- Given any auth flow, when browser storage is inspected, then it contains no tokens, passwords or emails.

## Implementation Notes

- Session layer in `apps/web/src/auth/` (provider, guards, pages, form parts, `authApi.ts`); routes and shell wired in `src/app/`. No new dependencies, no backend changes, generated API types untouched.
- Decision: `/reset-password` is NOT redirected when signed in (the spec lists it among the four routes but a reset link must work for a signed-in Learner); sign-up, sign-in and forgot-password do redirect. Revisit if you want it redirected too.
- Decision: the CSRF priming call is skipped when a `csrftoken` cookie already exists; otherwise `GET /auth/csrf/` runs before the unsafe request.
- Decision: a failed `/auth/me/` that is not 401/403 (network, 5xx) shows a "couldn't check your session" screen with Try again instead of silently treating the user as signed out.
- Sign-up checks empty fields and the 18+ box client-side (no request sent); the server still validates everything.
- Tests: 28 new Vitest tests in `src/auth/auth.test.tsx` (fetch mocked via `src/test/mockApi.ts`) cover every matrix row plus focus-to-summary, busy state and no-storage assertions; `AppShell.test.tsx` now starts signed in and the keyboard test includes the Sign out stop. Totals: 52 web tests pass.
- Verification (2026-10-29): `npm run lint`, `typecheck`, `test` (52 passed), `build` all pass; backend `pytest` 105 passed.
- Live end-to-end (Edge headless via playwright-core, Vite dev server + Django runserver, DEBUG, console email backend), all steps passed: guard redirect `/` -> `/sign-in`; sign-up blocked without 18+ (summary focused); sign-up signs in and the shell shows the email; sign out -> `/sign-in`; wrong password shows the generic message; sign in; forgot-password confirmation; reset link read from the API console output; password changed; old password rejected; sign in with the new password; `localStorage` and `sessionStorage` were empty; reusing the link shows the invalid/expired state. The local dev database had no migrations applied, so `manage.py migrate` was run once against it. Both servers were stopped afterwards.

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `npm run lint && npm run typecheck && npm run test && npm run build` (repo root) -- expected: all pass
- `cd apps/api && .venv/Scripts/python -m pytest -q` -- expected: 105 passed

## Orchestrator Review (2026-10-29)

- Re-ran independently against baseline f86114c: lint 0 warnings, typecheck, vitest 52 passed (28 new), build ok; backend pytest 105 passed, ruff clean. No stray servers.
- Storage scan: only the sidebar-collapse flag uses localStorage; CSRF cookie is read, never written; no auth data stored. Return-to-page uses router state and `readReturnTo` accepts only in-app paths (rejects `//` and auth paths), so no open redirect.
- Accepted judgment calls: `/reset-password` is reachable while signed in; a failed `/auth/me/` (network/5xx) shows a retry screen instead of signing the user out.
- Not verified: no screenshots of the sign-out footer at the three breakpoints; `npm ci` from a clean checkout not rerun for this story (done for 1.1).
