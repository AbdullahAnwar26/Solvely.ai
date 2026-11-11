---
title: 'Story 2.1: Create and open a Lesson with an empty Board'
type: 'feature'
created: '2026-10-29'
status: 'done'
baseline_commit: 'efc860b'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-Solvely.ai-2026-10-27/ARCHITECTURE-SPINE.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Solvely.ai-2026-10-28/DESIGN.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Solvely.ai-2026-10-28/EXPERIENCE.md'
  - '{project-root}/docs/ARCHITECTURE_NOTES.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A Learner has nowhere to work: there is no Lesson record and no Board. Every later feature (autosave, teaching, practice) hangs off a Lesson that the Learner owns.

**Approach:** Add the first real owned model, `Lesson`, with create, retrieve and list endpoints built on the Story 1.4 ownership base; add a "New lesson" action in the shell that creates a Lesson and opens `/lessons/:id`, where an Excalidraw Board loads lazily and is cleaned up on leave.

## Boundaries & Constraints

**Always:** Backend app `lessons`. `Lesson(OwnedModel)` with a UUID primary key, `title` (max 120, default "Untitled lesson"), `current_revision` integer default 0 (revision 0 means the empty Board; there is NO BoardRevision table or Board payload yet, that is Story 2.3), plus the inherited owner and timestamps. Endpoints under `/api/v1/lessons/`: `POST` create (optional `title`; owner is always `request.user`), `GET /{id}/` retrieve, `GET /` list (paginated, newest first). Build them on `OwnedModelViewSet`/mixin restricted to those three actions; foreign or missing ids return the standard 404 envelope. Register the endpoint with the isolation harness in `tests/isolation.py` (extend `register_owned_endpoint` to declare which actions exist, and fix id comparison to use `str()` for UUID ids); the registry guard test must pass. Every view keeps `@extend_schema` so `spectacular --validate --fail-on-warn` passes; regenerate `packages/shared` types. Rate-limit creation per user with a named constant in `core/limits.py` (e.g. 60/hour). Web: "New lesson" is a real primary action at the top of the sidebar (and drawer) that calls create, shows a busy state, navigates to `/lessons/:id`, and shows a clear error on failure; the route is lazy-loaded; the page fetches the Lesson, shows its title, and renders Excalidraw from `@excalidraw/excalidraw` (lazy `import()`; verify the installed version supports React 19 at install time and record it; import its CSS; pin the version exactly) filling the main area; theme follows the app theme (Excalidraw `theme` prop from the resolved light/dark); the Board unmounts cleanly on leave (no leaks, no console errors); not-found state for foreign, missing or malformed ids (reuse the not-found page style, accessible); loading and error states per EXPERIENCE.md. Board edits are NOT persisted in this story, and the UI must not show a save indicator or imply saving. Keyboard operable with visible focus; tokens only.

**Never:** No saving, revisions, undo/redo UI work, tools customisation, AI, rename, delete, archive or search (Stories 2.2 to 2.4 and Epic 6). No BoardRevision model. No fake data. No new dependencies other than `@excalidraw/excalidraw` (and what it strictly requires).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Create default | POST `{}` signed in | 201 `{id (uuid), title:"Untitled lesson", current_revision:0, created_at, updated_at}`; owner is caller | N/A |
| Create titled | POST `{"title":"Big-O"}` | 201 with that title | too long or blank-only -> 400 `validation_error` |
| Client sets owner | POST with `owner` of another user | ignored; owner is caller | N/A |
| Anonymous | no session | 403 `not_authenticated` | envelope |
| No CSRF | POST without token | 403 `csrf_failed` | envelope |
| Retrieve own | GET own id | 200 | N/A |
| Retrieve foreign/missing | other user's or random uuid | 404 `not_found`, same body for both | envelope |
| Malformed id | GET `/lessons/not-a-uuid/` | 404 `not_found` (not 500) | envelope |
| List | two users with lessons | only caller's, newest first, paginated | N/A |
| Methods | PUT/PATCH/DELETE on a lesson | 405 | envelope |
| Throttled | over the create rate | 429 `throttled`, retryable | envelope |
| New lesson UI | click New lesson | busy state, navigate to `/lessons/:id`, Board visible | create fails -> inline error, stays put |
| Open lesson | `/lessons/:id` | title shown, Board loads lazily with loading state | fetch error -> error state with retry |
| Foreign id in UI | `/lessons/<other user's id>` | accessible not-found state with link home | N/A |
| Leave page | navigate away | Board unmounts, no console errors | N/A |
| Theme | OS or app dark | Board uses dark theme | N/A |

</frozen-after-approval>

## Code Map

- `apps/api/core/ownership.py`, `core/viewsets.py` -- reuse (do not weaken); `tests/isolation.py`, `tests/test_ownership.py` -- extend registry for per-endpoint action sets and UUID ids.
- `apps/api/lessons/` -- new app: `models.py`, migration, `serializers.py`, `views.py`, `urls.py`, `apps.py`; register in `config/settings.py` INSTALLED_APPS and `config/urls.py`.
- `apps/api/core/limits.py`, `config/settings.py` -- add throttle rate and scope.
- `apps/api/tests/test_lessons.py` -- new.
- `packages/shared/src/generated/api.ts` -- regenerate (`npm run gen:api`, API running).
- `apps/web/src/` -- `lessons/` (api calls, LessonPage, NewLessonButton, board wrapper), routes, shell nav; `package.json` for the Excalidraw pin.
- `docs/ARCHITECTURE_NOTES.md` -- short note: Lesson as the first owned model, revision 0 semantics, Excalidraw version and lazy-loading approach.

## Tasks & Acceptance

**Execution:**
- [x] backend `lessons` app, model, migration, serializers, views, urls, throttle, schema decorators
- [x] extend isolation harness for action sets and UUID ids; register the lessons endpoint
- [x] `tests/test_lessons.py`: one test per backend matrix row
- [x] regenerate shared API types
- [x] web: Excalidraw dependency (exact pin), lazy Board component, LessonPage, NewLessonButton in shell, route, states
- [x] web tests: one per matrix row runnable in jsdom (mock the Excalidraw module; assert lazy load, unmount cleanup call, not-found, error and retry, busy state, navigation)
- [x] real browser check against the live API (Edge headless via playwright-core installed ONLY in the scratchpad directory, never in the repo): sign up, click New lesson, draw a shape on the real Excalidraw canvas, navigate away and back without console errors, foreign id shows not-found; stop every server you start and confirm ports 5173 and 8000 are free
- [x] docs note

**Acceptance Criteria:**
- Given a signed-in Learner, when they click New lesson, then a Lesson with `current_revision` 0 exists and `/lessons/:id` shows a working Excalidraw Board.
- Given another Learner's Lesson id, when it is requested through the API or the UI, then the result is the standard not-found with no data leaked.
- Given a clean checkout, when root `npm run lint`, `typecheck`, `test`, `build` and backend `pytest`, `ruff check`, `makemigrations --check`, `spectacular --validate --fail-on-warn` run, then all pass.

## Implementation Notes

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `npm run lint && npm run typecheck && npm run test && npm run build` (repo root) -- expected: all pass
- `cd apps/api && .venv/Scripts/python -m pytest -q && .venv/Scripts/python -m ruff check . && .venv/Scripts/python manage.py makemigrations --check` -- expected: pass, no changes
- `DJANGO_SETTINGS_MODULE=config.settings DJANGO_SECRET_KEY=x .venv/Scripts/python manage.py spectacular --validate --fail-on-warn --file /dev/null` -- expected: exit 0

## Orchestrator Review (2026-10-29)

- Re-ran independently after deleting node_modules and `npm ci`: React resolves to 19.3.1 everywhere (root `overrides` required, see note), lint 0 warnings, typecheck, vitest 73 passed, build ok (chunk-size warning for the lazy Board chunk). Backend pytest 138 passed, ruff clean, `makemigrations --check` clean, spectacular `--fail-on-warn` exit 0. Ports 5173/8000 free.
- Read `lessons/models.py` and `views.py`: built on `OwnedQuerysetMixin`, only create/retrieve/list, owner set server-side, extend_schema on all actions, isolation harness extended for action sets and UUID ids.
- Agent's live Edge run: sign-up, New lesson, Board loads in dark theme, rectangle drawn, unmount/remount clean, foreign and malformed ids show not-found, no third-party requests; the 10 test users it created were deleted from the dev DB.
- Not verified: Excalidraw text fonts (possible CDN fetch) because the live run only drew a rectangle; check in Story 2.2.
- Keep: root `package.json` `overrides` pinning react/react-dom to 19.3.1; without it Excalidraw's Radix deps hoist React 18 and tests fail.
