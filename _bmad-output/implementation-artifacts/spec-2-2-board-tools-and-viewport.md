---
title: 'Story 2.2: Board editing tools and viewport controls'
type: 'feature'
created: '2026-10-29'
status: 'done'
baseline_commit: '56e9b5f'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-2-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-2-1-create-and-open-lesson.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-Solvely.ai-2026-10-27/ARCHITECTURE-SPINE.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Solvely.ai-2026-10-28/DESIGN.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Solvely.ai-2026-10-28/EXPERIENCE.md'
  - '{project-root}/_bmad-output/implementation-artifacts/deferred-work.md'
  - '{project-root}/docs/ARCHITECTURE_NOTES.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The Board opens but is a bare Excalidraw canvas: learner-made elements are not marked as the Learner's own (AD-3 needs `origin`), zoom, fit and undo/redo are not clearly reachable, text fonts may be fetched from a third-party CDN, and the Board is not verified at tablet and phone sizes.

**Approach:** Wrap the Board with accessible app-level controls, tag every learner-created element with `customData.origin = "learner"`, self-host Excalidraw's fonts and assets so nothing is fetched from third parties, and verify touch and keyboard behaviour across breakpoints.

## Boundaries & Constraints

**Always:** Use only documented `@excalidraw/excalidraw` 0.18.1 APIs (imperative `excalidrawAPI`, `onChange`, `updateScene`, `scrollToContent`, `CaptureUpdateAction`, `getAppState`, `getSceneElements`); no internals, no forks. Every element created by the Learner gets `customData: { origin: "learner" }` (preserve any existing customData keys; never overwrite an existing `origin`); tagging must not create an update loop, must not add undo history entries, and must not make saved-looking changes (there is still no saving; Story 2.3). Controls rendered by the app (real `<button>`s, tokens only, visible focus, labels, `aria-pressed` or disabled states where relevant): zoom in, zoom out, reset zoom to 100%, fit to content (fit-to-content on an empty Board must be a safe no-op or disabled), and undo and redo. If the documented API has no undo/redo method, rely on Excalidraw's own built-in undo/redo controls and keyboard shortcuts, keep them visible and reachable at every breakpoint, and record the finding in Implementation Notes instead of using internals. Zoom level is shown as a percentage in a polite live region. Keyboard: documented Excalidraw shortcuts work when the canvas is focused; the app controls have a logical Tab order and do not trap focus; Escape never discards work. Fonts and assets: configure Excalidraw's asset path (`window.EXCALIDRAW_ASSET_PATH` or the documented equivalent) so fonts load from this origin; copy only the needed asset files into the build (a committed folder under `apps/web/public/` is acceptable if the added size is under 3 MB, otherwise a build-time copy script with no new dependency); the production build and the dev server must both work; no request to any third-party host while drawing text, shapes, freehand and using the library. Layout: Board fills the main area on laptop, tablet and phone; app controls reflow (compact on phone, no horizontal page scroll); touch drawing, pinch zoom and pan work in a real browser at 820 and 390 px. Respect reduced motion for app-owned transitions. Keep the lazy loading and unmount cleanup from Story 2.1.

**Never:** No saving, revisions or save indicator (Story 2.3). No AI, no teaching panel, no export or import (Epic 6 and later). No new runtime dependencies (a dev-only helper is fine if justified). Do not change backend code. Do not modify Learner element content except adding `customData.origin` when absent.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Draw shape | Learner draws a rectangle | element has `customData.origin === "learner"`; no extra undo entry beyond the draw | N/A |
| Text and freehand | text, arrow, freehand | same tagging; text uses self-hosted fonts | N/A |
| Existing origin | element already has `origin: "ai"` (injected in test) | left unchanged | N/A |
| Existing customData | element with other customData keys | keys preserved, `origin` added only if absent | N/A |
| Update loop guard | any edit | tagging runs once per new element, no render loop | N/A |
| Zoom controls | click zoom in/out/reset | zoom changes; percentage text updates; announced politely | at min/max zoom the button disables |
| Fit to content | Board with elements | viewport fits content | empty Board: control disabled or no-op, no error |
| Undo/redo | draw, undo, redo | state follows; controls reachable by mouse and keyboard | nothing to undo: disabled (or Excalidraw built-in) |
| Keyboard | Tab to controls | logical order; visible focus; Enter/Space activate | N/A |
| Fonts | draw text, watch network | no request to third-party hosts; fonts from this origin | missing asset: text still renders with fallback, no crash |
| Responsive | 1280, 820, 390 px | Board fills area; controls reflow; no horizontal page scroll | N/A |
| Touch | pinch zoom and pan at 390 px | works on the canvas | N/A |
| Cleanup | navigate away | listeners removed, no console errors | N/A |
| Theme | OS dark/light and app setting | controls and canvas follow the resolved theme | N/A |

</frozen-after-approval>

## Code Map

- `apps/web/src/lessons/Board.tsx`, `LessonPage.tsx` -- existing lazy Board; extend with the `excalidrawAPI` handle, `onChange` tagging, controls bar.
- `apps/web/src/lessons/` -- new: origin tagging helper (pure, unit-tested), `BoardControls.tsx`, styles using tokens.
- `apps/web/vite.config.ts`, `apps/web/index.html`/`main.tsx` -- asset path setup; `apps/web/public/` or a build copy script for fonts.
- `apps/web/src/test/` -- Excalidraw mock helpers exist from Story 2.1; extend.
- `docs/ARCHITECTURE_NOTES.md` -- notes: origin tagging, undo/redo finding, asset self-hosting.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- the font and bundle-size item from Story 2.1 is addressed here; append a RESOLVED line.

## Tasks & Acceptance

**Execution:**
- [x] pure helper to tag elements with `origin: "learner"` (idempotent, preserves customData) + unit tests for every tagging row
- [x] wire tagging through `onChange` + `updateScene` with `CaptureUpdateAction.NEVER` and a loop guard; verify in the real browser that the history stack is not polluted
- [x] `BoardControls`: zoom in/out/reset, fit to content, undo/redo (or documented built-in fallback), live zoom percentage, tokens, responsive
- [x] self-hosted fonts and assets; prove no third-party requests in a real browser while drawing text
- [x] web tests (jsdom, Excalidraw mocked): helper, controls states, labels and keyboard activation, cleanup
- [x] real browser checks (Edge headless via playwright-core installed ONLY in the scratchpad directory, never in the repo) at 1280, 820, 390: draw rectangle/text/freehand, inspect element `customData`, undo/redo, zoom and fit, network log shows no third-party hosts, no console errors, no horizontal scroll; stop every server you start and confirm ports 5173 and 8000 are free
- [x] docs notes and the deferred-work RESOLVED line

**Acceptance Criteria:**
- Given a Learner drawing any element, when inspected via the Excalidraw API, then it carries `customData.origin === "learner"` and undo history contains no tagging-only entries.
- Given text drawn on the Board, when network requests are recorded, then none go to a third-party host.
- Given the Board at 1280, 820 and 390 px, when used with keyboard and touch, then zoom, fit, undo and redo are reachable and the page has no horizontal scroll.
- Given a clean checkout, when root `npm run lint`, `typecheck`, `test`, `build` and backend `pytest`, `ruff check` run, then all pass (backend unchanged, 138 passed).

## Implementation Notes

- Undo/redo finding: Excalidraw 0.18.1's documented imperative API has no undo/redo method (only `history.clear`), so the built-in Excalidraw buttons and Ctrl/Cmd+Z shortcuts are used; they were visible at 1280, 820 and 390 px.
- Tagging waits while `newElement`, `editingTextElement` or `multiElement` is set; a "same array returned" check is the loop guard. Real Edge run: one undo removes a new rectangle, redo restores it tagged.
- Fonts self-hosted in `apps/web/public/excalidraw-assets/fonts` (~500 KB; 13 MB Xiaolai CJK font excluded). Edge network log showed only localhost:5173.
- Excalidraw's footer also has zoom buttons, so two zoom sets exist at runtime.
- Dev-mode console warning from Excalidraw's own `_App` at 390 px (setState inside updater) is library-internal.

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `npm run lint && npm run typecheck && npm run test && npm run build` (repo root) -- expected: all pass
- `cd apps/api && .venv/Scripts/python -m pytest -q && .venv/Scripts/python -m ruff check .` -- expected: 138 passed, clean

## Orchestrator Review (2026-10-29)

- Re-ran independently: web lint 0 warnings, typecheck, vitest 94 passed, build ok (fonts present in `dist/excalidraw-assets/fonts`, 500 KB source folder); backend pytest 138 passed, ruff clean. Ports 5173/8000 free, no leftover servers.
- Read `originTag.ts`: pure and idempotent, preserves customData, never overwrites an existing origin, skips deleted elements, returns the same array when nothing changes (this is the loop guard); Board waits while an element is being drawn or typed.
- Agent's live Edge run (1280/820/390, dark): rectangle, text, freehand and arrow tagged `origin: "learner"`; one Ctrl+Z removed a fresh rectangle and redo restored it tagged (no extra history entry); zoom/fit controls and live region work; no third-party hosts; touch pinch, pan and draw work at 390 px; no horizontal scroll.
- Findings accepted: Excalidraw 0.18.1 has no documented undo/redo API, so built-in buttons and Ctrl/Cmd+Z are used; two sets of zoom buttons exist at runtime (app bar and Excalidraw footer).
- Not verified: production build was not exercised in a browser (only the dev server).
