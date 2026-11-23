---
title: 'Story 2.4: Resume after refresh or interruption'
type: 'feature'
created: '2026-10-29'
status: 'done'
baseline_commit: 'e2922ce'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-2-3-autosave-revisions.md'
  - '{project-root}/_bmad-output/implementation-artifacts/deferred-work.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Solvely.ai-2026-10-28/EXPERIENCE.md'
  - '{project-root}/docs/ARCHITECTURE_NOTES.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** A Learner whose save failed, whose tab crashed, or who only panned or zoomed can lose recent work or return to a different view. The save label also keeps saying "Saved" for up to 1.5 s after a real edit.

**Approach:** Restore the saved viewport on open, keep a device-local draft only while changes are unsaved so they can be offered back after a reload, never auto-restore a draft that could overwrite newer server work, and flip the save label to "Unsaved changes" as soon as a real content change happens.

## Boundaries & Constraints

**Always:** Web only (no backend change; if a backend gap blocks you, stop and report). Viewport: the saved `app_state` (`scrollX`, `scrollY`, `zoom`) is applied when a revision is loaded; a viewport-only change (pan or zoom) with no content change is saved with the next content save, and must not trigger a save by itself or flip the label to Unsaved. Dirty detection: on Excalidraw `onChange`, compute a cheap element-version sum (or equivalent O(n) over live elements, no JSON serialization and no allocation per element) and compare it with the last saved or loaded value; when different set the status to a new `unsaved` state shown as "Unsaved changes" (polite live region, never "Saved"); selection or viewport changes must not flip it. Keep the debounce, single in-flight save, retries and conflict behaviour from Story 2.3 unchanged. Local draft: while content is unsaved (status unsaved, saving, error, or conflict) write the current serialized board plus `{lesson_id, user_id, base_revision, saved_at}` to `localStorage` under the key `wt.draft.<userId>.<lessonId>` (inside try/catch; skip silently if storage is unavailable or the value exceeds about 1.5 MB); throttle writes (at most one per 2 s and always before `pagehide`/`beforeunload`); delete the draft as soon as the server confirms the content (revision saved or retried successfully) and when the Learner chooses Discard or Reload latest. Never keep drafts for other users: on sign-out and on account deletion remove every `wt.draft.*` key, and ignore any draft whose `user_id` differs from the signed-in user. On open, after the server board loads: if a draft exists for this user and lesson, `draft.base_revision === server revision`, and its element fingerprint differs from the server board, show a non-blocking recovery banner "We found unsaved changes from this device" with buttons Restore and Discard (focus management and keyboard operable, polite announcement). Restore loads the draft board into Excalidraw (documented restore helpers, keep `customData`), marks status unsaved and lets autosave persist it with the current base revision. Discard deletes the draft. If `draft.base_revision < server revision` (the Lesson changed elsewhere since), never auto-restore: show an informational banner "Your unsaved changes on this device are based on an older version and can't be merged" with a Discard button; keep the draft until Discard (so the Learner is not silently deprived). If the draft equals the server content, delete it silently. Banners use tokens, the existing alert styling and copy in the EXPERIENCE.md voice (calm, plain, never blaming). The storage-test (`auth.test.tsx`) rule stays: no tokens, passwords or emails in storage; allow only keys `wt.theme`, `wt.sidebar...` (existing) and `wt.draft.*`, and assert draft values contain only board data and the listed metadata.

**Never:** No backend change, no duplicate-as-copy flow, no export, no AI, no IndexedDB, no new dependencies, no change to ownership or API contracts. Do not store drafts for signed-out users. Do not restore a draft automatically.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Viewport restore | saved revision with scroll/zoom | Board opens at that viewport | missing or invalid app_state: default view |
| Pan only | pan or zoom, no content change | status stays Saved, no save request | N/A |
| Dirty flip | draw a shape | status becomes Unsaved changes immediately, then Saving, then Saved | N/A |
| Select only | select or deselect | status unchanged | N/A |
| Draft written | unsaved content | `wt.draft.<user>.<lesson>` written, throttled, flushed on pagehide | storage unavailable or too large: skipped silently |
| Draft cleared | save confirmed | draft key removed | N/A |
| Failed save then reload | PUT fails, reload | last good revision loads; recovery banner offered; Restore loads draft and marks Unsaved | N/A |
| Restore then autosave | after Restore | autosave persists with current base revision | conflict -> existing Conflict flow |
| Discard | click Discard | draft removed, banner closes, board unchanged | N/A |
| Equal draft | draft equals server board | removed silently, no banner | N/A |
| Stale draft | draft base < server revision | informational banner with Discard only; no auto-restore; draft kept until Discard | N/A |
| Other user's draft | `user_id` mismatch | ignored and not shown | N/A |
| Sign-out / delete account | | all `wt.draft.*` removed | N/A |
| Corrupt draft | invalid JSON or schema | ignored and removed | N/A |
| Storage test | full auth flows | only allowed keys present | N/A |
| Accessibility | banners | keyboard operable, focus not stolen, polite announcement | N/A |

</frozen-after-approval>

## Code Map

- `apps/web/src/lessons/useAutosave.ts`, `boardSerialize.ts`, `Board.tsx`, `LessonPage.tsx`, `SaveStatus.tsx`, `board.css` -- extend (unsaved state, dirty detection, viewport restore, draft hooks, banners).
- `apps/web/src/lessons/draftStorage.ts` -- new: pure draft read/write/clear helpers with validation (unit tested).
- `apps/web/src/auth/` -- sign-out and account deletion must call the draft cleanup (find the existing hooks in `SessionProvider.tsx`, `SettingsPage.tsx`/`DeleteAccountDialog.tsx`).
- `apps/web/src/auth/auth.test.tsx` -- update the storage test as specified.
- `docs/ARCHITECTURE_NOTES.md` -- notes on viewport restore, dirty detection, draft lifecycle and privacy.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- append RESOLVED lines for the items this story closes.

## Tasks & Acceptance

**Execution:**
- [x] `draftStorage.ts` with validation and unit tests for every draft row
- [x] unsaved state and cheap dirty detection in the autosave machine, with tests (pan-only and select-only do not flip it)
- [x] viewport restore on load with tests
- [x] draft write/clear lifecycle and cleanup on sign-out and account deletion, with tests
- [x] recovery banners (Restore, Discard, stale notice) with tests including keyboard and announcements
- [x] update the storage test; docs notes; deferred-work RESOLVED lines
- [x] real browser check against the live API (Edge headless via playwright-core installed ONLY in the scratchpad directory, never in the repo): draw, simulate a failed save (abort PUT), reload, see last good content plus the recovery banner, Restore, Saved; pan-only does not change the label; stale-draft banner via a second tab; sign-out removes draft keys; stop every server you start and confirm ports 5173 and 8000 are free

**Acceptance Criteria:**
- Given a failed save followed by a reload, when the Lesson opens, then the last good revision shows and the Learner can restore or discard the unsaved device draft, and Restore never overwrites newer server work.
- Given a saved viewport, when the Lesson is reopened, then the Board opens at that viewport.
- Given any real content edit, when the change happens, then the label reads Unsaved changes before the save starts, and panning alone does not.
- Given a clean checkout, when root `npm run lint`, `typecheck`, `test`, `build` and backend `pytest`, `ruff check` run, then all pass (backend unchanged, 208 passed).

## Implementation Notes

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `npm run lint && npm run typecheck && npm run test && npm run build` (repo root) -- expected: all pass
- `cd apps/api && .venv/Scripts/python -m pytest -q && .venv/Scripts/python -m ruff check .` -- expected: 208 passed, clean

## Orchestrator Review (2026-10-29)

- Re-ran independently: web lint 0 warnings, typecheck, vitest 172 passed, build ok; backend pytest 208 passed, ruff clean (backend unchanged). Ports free, no leftover servers.
- Read `draftStorage.ts`: key `wt.draft.<userId>.<lessonId>`, stored fields limited to board plus `lesson_id`, `user_id`, `base_revision`, `saved_at`; strict validation; user or lesson mismatch and corrupt data are ignored and removed; size cap 1.5 MB; every storage call in try/catch; writer only deletes the exact text it stored.
- Agent's live Edge run: pan-only keeps Saved with no PUT; drawing flips to Unsaved changes within 1 s; aborted PUT writes a draft; reload shows last good revision plus the recovery banner; Restore saves as the next revision and removes the draft; stale-draft banner with Discard only after a second tab saved; sign-out removes all drafts.
- Accepted judgment calls and follow-ups: a second tab does not get its own draft protection while another tab's draft for that lesson is unresolved; Restore replaces the whole scene (including edits made after opening) without a confirm; every Saved to Unsaved transition is announced (slightly noisier). Mixed CRLF/LF line endings in touched files are normalised by git.
