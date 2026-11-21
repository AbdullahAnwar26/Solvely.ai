---
title: 'Story 2.3: Autosave with revisions and conflict protection'
type: 'feature'
created: '2026-10-29'
status: 'done'
baseline_commit: '0bf1923'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-2-1-create-and-open-lesson.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-2-2-board-tools-and-viewport.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-Solvely.ai-2026-10-27/ARCHITECTURE-SPINE.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Solvely.ai-2026-10-28/EXPERIENCE.md'
  - '{project-root}/docs/ARCHITECTURE_NOTES.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Board edits vanish on reload. Without revisions and conflict checks, a stale tab or a retried request could silently overwrite newer work, and a first autosave over an unloaded Board would destroy stored work.

**Approach:** Persist the Board as append-only, numbered revisions with optimistic concurrency (AD-4): a save carries its base revision, a mismatch returns 409 and never overwrites, retries are idempotent through a client save id, and the web app autosaves after a debounce, loads the latest revision when a Lesson opens, and shows an honest save status.

## Boundaries & Constraints

**Always (backend):** New model `BoardRevision(OwnedModel)`: FK to `Lesson` (cascade), `revision` positive integer, `payload` JSONField, `save_id` UUID, plus owner and timestamps; unique `(lesson, revision)` and unique `(lesson, save_id)`; owner is always set server-side from the Lesson's owner, never from the request. Revision 0 stays implicit (empty Board, no row). Endpoints under `/api/v1/lessons/{lesson_id}/board/`: `GET` returns `{revision, board}` for the latest revision (revision 0 returns an empty valid board); `PUT` accepts `{base_revision, save_id, board}`. PUT algorithm inside one `transaction.atomic()` with the Lesson row locked (`select_for_update`): if a revision with this `save_id` already exists for the Lesson return 200 with that revision (idempotent retry, no new row); else if `base_revision != lesson.current_revision` return 409 with error code `revision_conflict` and `current_revision` in the envelope (extend the envelope helper minimally, keeping the standard fields); else validate, insert revision `base_revision + 1`, set `lesson.current_revision`, return 200 `{revision}`. Never overwrite or update an existing revision row. Pruning by policy only: after a successful save keep the latest 50 revisions and delete older ones in the same transaction (named constant). Payload validation (strict, server-side, named constants in `core/limits.py`): `board` is an object with `schema_version` equal to 1 and only the allowed keys `elements` (list), `app_state` (small object limited to `viewBackgroundColor`, `scrollX`, `scrollY`, `zoom` as `{value}` numbers); no `files` key (images are out of scope); at most 5000 elements; total JSON body at most 2 MB (reject larger with 413 or 400 using the envelope); each element must be an object with string `id` (max 64), `type` in the closed Excalidraw type set (`rectangle`, `diamond`, `ellipse`, `arrow`, `line`, `freedraw`, `text`, `frame`), finite numeric `x`, `y`, `width`, `height` within sane bounds, text length capped, string fields length-capped, and `customData.origin` (when present) in {`learner`, `ai`}; unknown element types or non-finite numbers reject the whole payload (no partial save). Auth: authenticated, CSRF on PUT, owner-scoped Lesson lookup so foreign or missing lesson ids return the standard 404; per-user save throttle with a named rate. Every view has `@extend_schema`; the OpenAPI must pass `spectacular --validate --fail-on-warn`; regenerate `packages/shared` types. Register the board endpoint (and `BoardRevision`) with the isolation harness so the registry guard passes.

**Always (web):** Autosave: debounce (about 1.5 s) after the last change, serialize only then (compare a cheap element version fingerprint to skip unchanged scenes; do no work on every frame); never save while the load is unfinished; send `{base_revision, save_id, board}` where the board is built from documented Excalidraw APIs (`getSceneElements`, minimal `appState` fields above; drop `files`; disable or hide the image tool through the documented `UIOptions` so images cannot be created); keep exactly one save in flight and coalesce further changes; a new `save_id` per attempt of new content, the same `save_id` when retrying the same content. On open, GET the latest revision and load it into Excalidraw with documented restore helpers before enabling saving; elements keep their `customData`. Save status indicator in the Board header (EXPERIENCE.md save states): Saved, Saving, Not saved (with Retry), and Conflict; announced politely, never claiming Saved unless the server confirmed. On failure retry with bounded exponential backoff (cap the attempts, then stay in Not saved with a manual Retry). On 409: stop autosaving, show a clear Conflict state explaining that this lesson was changed elsewhere, offer Reload latest (which discards the local unsaved changes only after confirmation) and never auto-overwrite. Warn with the browser `beforeunload` prompt while unsaved changes exist. Tokens only, keyboard operable, no new runtime dependencies.

**Never:** No AI, no teaching steps, no rename/delete/archive, no export, no local-draft recovery (Story 2.4), no image support, no change to Story 1.x auth behaviour. Do not weaken ownership checks. Do not store board content in browser storage.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| First save | PUT base 0 valid board | 200 `{revision:1}`, revision row 1, lesson.current_revision 1 | N/A |
| Next save | PUT base 1 | 200 revision 2 | N/A |
| Stale base | PUT base 1 when current is 2 | 409 `revision_conflict` with `current_revision`, nothing written | envelope |
| Retry same save | same `save_id` again | 200 same revision, no new row | N/A |
| Concurrent saves | two PUTs same base | exactly one 200, the other 409 (or idempotent 200 if same save_id) | N/A |
| GET empty | revision 0 | 200 `{revision:0, board:{schema_version:1, elements:[]}}` | N/A |
| GET latest | after saves | latest payload | N/A |
| Foreign lesson | other user's lesson id on GET/PUT | 404 `not_found`, no data | envelope |
| Anonymous / no CSRF | | 403 `not_authenticated` / `csrf_failed` | envelope |
| Bad schema_version | `schema_version: 2` | 400 `validation_error` | no write |
| Unknown element type / NaN / Infinity | | 400, nothing saved | no write |
| Too many elements / too large | 5001 elements or over 2 MB | 400 or 413 envelope | no write |
| Owner spoof | payload or URL tries another owner | ignored; owner from lesson | N/A |
| Pruning | save #52 | only latest 50 rows remain; GET still returns latest | N/A |
| Throttled | over save rate | 429 `throttled` retryable | envelope |
| Autosave | edit then pause | one PUT after debounce, status Saving then Saved | N/A |
| Rapid edits | many edits within debounce | one PUT | N/A |
| Save fails | network or 5xx | Not saved with Retry, backoff then manual retry, content kept in memory | N/A |
| Conflict in UI | 409 | Conflict state, autosave stops, nothing overwritten, Reload latest offered | N/A |
| Open with content | revision > 0 | Board shows saved content before any save is allowed | GET fails -> error state, saving disabled |
| Unload while unsaved | | beforeunload prompt | N/A |
| Learner tags | saved elements | `customData.origin` round-trips | N/A |

</frozen-after-approval>

## Code Map

- `apps/api/lessons/` -- add `BoardRevision` model and migration, board serializers (strict validation), board view(s), URLs, throttle, schema decorators; reuse the Story 2.1 `LessonViewSet` lookup so ownership 404s are identical.
- `apps/api/core/limits.py` -- named constants for the limits above; `core/errors.py` -- minimal extension to carry `current_revision` on 409 (keep the standard fields).
- `apps/api/tests/isolation.py`, `test_ownership.py` -- extend the registry for the nested board endpoint and `BoardRevision`.
- `apps/api/tests/test_board_revisions.py` -- new; include a real concurrency test (two threads or `transaction` based) against PostgreSQL.
- `packages/shared/src/generated/api.ts` -- regenerate.
- `apps/web/src/lessons/` -- `boardApi.ts`, `useAutosave.ts` (state machine), `SaveStatus.tsx`, `Board.tsx` (load, restore, UIOptions), page wiring; pure serialization helper with unit tests.
- `docs/ARCHITECTURE_NOTES.md` -- notes on revisions, idempotency, pruning, payload limits, autosave state machine.

## Tasks & Acceptance

**Execution:**
- [x] backend model, migration, limits, strict payload validation, board GET/PUT with locking, idempotency, pruning, throttle, schema
- [x] extend isolation harness; regenerate shared types
- [x] backend tests: one per matrix row, plus a genuine concurrent-save test on PostgreSQL and a mutation check (temporarily break the base-revision check or the lock and confirm tests fail, then restore)
- [x] web: board API client, serialization helper (pure, tested), autosave state machine with debounce, single in-flight save, backoff, conflict handling, beforeunload
- [x] web: load latest revision on open, restore into Excalidraw, hide image tool, SaveStatus component with live region
- [x] web tests (jsdom, Excalidraw mocked): state machine rows, debounce coalescing, retry/backoff caps, conflict stops saving, no Saved claim before server confirmation, load-before-save, beforeunload
- [x] real browser check against the live API (Edge headless via playwright-core installed ONLY in the scratchpad directory, never in the repo): draw, wait, reload and see the same content; two tabs on one lesson produce a Conflict state on the stale tab and no overwrite; simulate a network failure then retry; stop every server you start and confirm ports 5173 and 8000 are free
- [x] docs notes

**Acceptance Criteria:**
- Given a Learner who draws and pauses, when the page is reloaded, then the same elements (with their origin tags) are shown and the status read Saved before reload.
- Given two tabs on the same Lesson, when the stale tab saves, then it shows Conflict, the newer content on the server is unchanged, and no data is overwritten.
- Given a retried save with the same `save_id`, when sent twice, then exactly one revision exists.
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

- Re-ran independently: backend pytest 208 passed (concurrency tests run twice, stable), ruff clean, `makemigrations --check` clean, spectacular `--fail-on-warn` exit 0; web lint 0 warnings, typecheck, vitest 119 passed, build ok. Ports free, no leftover servers.
- Read `save_board`: one `transaction.atomic()`, owner-scoped locked lesson (`select_for_update` via `get_object`), order is idempotent `save_id` check, then `base_revision` conflict (409, rolled back), then strict validation, insert, `current_revision` update, pruning to the newest 50; body size refused from `Content-Length` before parsing. Agent's mutation checks (remove lock: 2 concurrency tests fail; disable base check: 3 tests fail) accepted.
- Agent's live Edge run: draw/pause/Saved then reload restores same element with `origin: "learner"` and sends no save; two tabs: stale tab shows Conflict and server keeps the newer revision; aborted PUTs show Not saved + Retry; `beforeunload` prompt works; no third-party requests, no JS errors.
- Accepted judgment calls and follow-ups: the label stays "Saved" (= last confirmed save) until the debounce fires, because serializing on every change was avoided (low severity, leaving the page is guarded); viewport-only changes are saved with the next content change; images or embeds that reach the scene are left out of saves; "Keep mine as a copy" not built.
