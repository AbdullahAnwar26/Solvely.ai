# Epic 1 Context: Accounts and a Private Learning Space

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Learners (adults 18+) can safely sign up, sign in, recover access, work inside a responsive web app shell, see only their own data, and delete their account and all data. This epic also stands up the web app (`apps/web`), which does not exist yet; the Django backend foundation in `apps/api` (DRF, health/ready, request-ID middleware, pytest on PostgreSQL) already exists. It is the security and privacy base every later epic builds on.

## Stories

- Story 1.1: Web app shell and API client
- Story 1.2: Registration with 18+ confirmation
- Story 1.3: Sign in, sign out, password reset
- Story 1.4: Owner-scoped data foundation
- Story 1.5: Account deletion

## Requirements & Constraints

- Registration requires email, password and an 18+ confirmation; the confirmation timestamp is stored. Duplicate emails and weak passwords are rejected.
- Sessions are secure; password reset is by email, single-use, expiring, and never reveals whether an email exists.
- Registration and login are rate limited/throttled.
- A Learner can access only their own data; other users' object ids return 404.
- Account deletion requires password confirmation, removes the user and all owned records in one transaction, invalidates old sessions, and leaves no orphaned rows.
- The shell must be responsive (laptop, tablet, phone) and keyboard operable with visible focus.
- No stack traces in responses; no passwords or student content in logs; secrets never in the browser.

## Technical Decisions

- Auth: Django session cookie (HttpOnly, SameSite=Lax, Secure in production) plus CSRF on unsafe methods. No tokens in browser storage. Production serves SPA and API from one origin; dev uses the Vite proxy.
- Ownership: every owned model has an `owner` FK via a shared `OwnedModel` base and a `for_user(request.user)` manager. Views get querysets only through it; owner is never a request field. A cross-user test suite covers every owned endpoint, and new endpoints must register in it.
- API: prefix `/api/v1/`; OpenAPI (drf-spectacular) is the contract; web client types are generated from it (into `packages/shared`). Single error envelope `{ "error": { "code", "message", "retryable", "request_id" } }` with stable string codes.
- Frontend: React 19 + TypeScript strict + Vite in `apps/web`, with lint, type-check, Vitest (+ Testing Library) and build commands. Pin the TypeScript major only after a toolchain compatibility check. Server state goes through one query layer.
- Backend layout: `accounts/` holds users, 18+ confirmation, preferences; `core/` holds health, request id, error envelope, limits. Limits are named constants in one `limits` module per side.
- Conventions: snake_case Python and API JSON fields, PascalCase React components, UTC ISO 8601 timestamps, structured JSON logging with `request_id`, config via environment variables (`.env.example` only). Tests: backend pytest, frontend Vitest.

## UX & Interaction Patterns

- Shell has a sidebar, a "New lesson" action and a content area; layout reorganises across laptop, tablet and phone widths.
- Keyboard operability and visible focus are required; the target is WCAG 2.2 AA for core flows, with light/dark themes. No UX design contract exists yet, so keep the shell simple and revisit when one is produced.

## Cross-Story Dependencies

- 1.4 provides the ownership base that all later owned models and endpoints (lessons, boards, practice, usage) must use.
- 1.1 provides the web shell and generated API client that 1.2, 1.3 and 1.5 UIs rely on; 1.2 and 1.3 share the session/CSRF setup.
- 1.5 deletion must cover all owned records, so it needs to be extended as later epics add owned models.
- Later epics depend on this one: Epic 2 onward needs authenticated, owner-scoped access and the web shell. A privacy notice is finalised in Epic 7.
