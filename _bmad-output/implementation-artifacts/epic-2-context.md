# Epic 2 Context: Editable Whiteboard Lessons

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

A Learner can start a Lesson, draw and edit on an Excalidraw Board, and have it autosave and resume exactly where they left off, with no AI involved. This establishes the Board, its persistence model and the Learner-Content origin marking that all later teaching epics build on.

## Stories

- Story 2.1: Create and open a Lesson with an empty Board
- Story 2.2: Board editing tools and viewport controls
- Story 2.3: Autosave with revisions and conflict protection
- Story 2.4: Resume after refresh or interruption

## Requirements & Constraints

- Board supports draw, select, move, resize, delete, zoom, pan, fit-to-content, undo/redo; Learner Content must be distinguishable from AI Content later.
- Board state persists with visible save status; resume restores the same elements and viewport and the same Step.
- A stale save is refused (409) and never overwrites newer work; payloads are validated for schema version and size limit (named constants in a `limits` module, mirrored by tests).
- A Lesson owned by someone else or deleted looks identical to the learner: a not-found state.
- Controls are keyboard accessible with visible focus and responsive at tablet and phone widths; targets at least 24px (44px on touch).
- No prompts or learner content in logs; errors use the single error envelope with request_id.

## Technical Decisions

- Board state lives in Excalidraw (0.18.x on React 19, loaded lazily, cleaned up on leave) and is serialized only on debounced save and Step change. Server state goes through the one query layer.
- Every element carries `customData.origin` in {`ai`, `learner`} and a stable `customData.stepId`; learner-drawn elements get `origin = "learner"`. AI ids will be `ai:<stepId>:<n>`. AI never edits learner elements.
- Board changes from AI will pass only through one typed frontend board adapter (closed Board Operation vocabulary); build the adapter as the sole seam to Excalidraw.
- `BoardRevision`: append-only rows, per-lesson integer `revision` starting at 0 for an empty Board; client sends base revision; mismatch returns 409 with the current revision; pruning by policy, never by update.
- Lessons are owned models: `owner` FK, `OwnedModel` base and `for_user(request.user)` manager, foreign ids return 404; owner is never a request field. New endpoints must be registered in the cross-user isolation test suite.
- API under `/api/v1/`, DRF, OpenAPI via drf-spectacular is the contract; web client types are generated from it into `packages/shared`. API JSON fields snake_case; ids UUID strings; timestamps UTC ISO 8601.
- Code layout: `apps/api/lessons` (lessons), `apps/api/board` (BoardRevision), `apps/web` (routes, board adapter, workspace). Tables are created by the story that needs them.
- Tests: backend pytest on PostgreSQL, frontend Vitest + Testing Library, an end-to-end edit-reload-verify test for resume.

## UX & Interaction Patterns

- Lesson opens at a workspace route (epics say `/lessons/:id`; UX spine proposes `/app/lessons/:id` and `/app/new`; routes are assumptions, reconcile with existing router).
- Empty Board shows immediately with Board background; skeletons on cold load, no spinner over the Board.
- Learner elements use hand-drawn styling (roughness 1, Excalifont, learner ink); origin badge ("You"/"Tutor") on select/hover/long-press and a "Show who drew what" toggle. Feasibility of badges and per-element defaults in Excalidraw 0.18 must be confirmed in Story 2.2.
- Excalidraw `theme` follows the active app theme; zoom-to-fit button and `Shift+1`.
- Save status in the panel header: Saved / Saving... / Couldn't save - Retry; debounced autosave (about 1.5 s idle, assumption) plus save on Step change; 3 automatic retries with backoff, then manual; announce only failures and recovery to screen readers.
- 409 conflict alert: "Load newer version" (primary) and "Keep mine as a copy" (duplicates Lesson with local Board); never silent overwrite.
- Offline banner: keep drawing, saves queue and flush on reconnect. `beforeunload` guard when unsaved. After failed save plus reload, last good revision loads and local unsaved changes are offered for recovery.
- Not-found copy: "We couldn't find that lesson." with a link to the library, identical for foreign and deleted ids.
- Excalidraw canvas is not screen-reader navigable; keyboard shortcuts are disabled while typing or in the canvas text editor; Esc/F6 leave Board focus.
- Voice: calm, honest, no emojis or celebratory copy.

## Cross-Story Dependencies

- Depends on Epic 1: web shell, auth session/CSRF, generated API client, owner-scoped foundation. Story 2.1 adds the "New lesson" action to the shell.
- 2.2 relies on 2.1 (Board loaded); 2.3 on 2.1 (Lesson and revision 0) and 2.2 (elements to save); 2.4 on 2.3 (revisions to load).
- Epic 3 reuses the origin marking, board adapter and revision model; Epic 4 and 6 reuse the 409/duplicate behaviour and Lesson ownership.
