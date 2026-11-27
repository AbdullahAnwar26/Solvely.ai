---
title: 'Story 3.3: Deterministic layout engine'
type: 'feature'
created: '2026-11-06'
status: 'done'
baseline_commit: '9340f7d'
route: 'dispatch'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-Solvely.ai-2026-10-27/ARCHITECTURE-SPINE.md'
  - '{project-root}/_bmad-output/planning-artifacts/epics.md'
  - '{project-root}/apps/api/domain/lesson_schema.py'
  - '{project-root}/apps/api/domain/board_operations.py'
---

## Intent

**Problem:** Provider output must never decide coordinates (FR-8): generated diagrams must not overlap, clip text, or leave the Learner looking at empty canvas.

**Approach:** `domain/layout.py` takes structured, provider-describable content (sequential solution, flowchart, concept map, code walkthrough) and returns ordinary `add_element` operations with provisional ids plus one `set_viewport`. Output goes straight into the existing Story 3.2 validator, which stays the only gate to the Board. Framework-free (stdlib + pydantic + `core.limits`).

## Acceptance (from epics.md) and how it is met

- No two elements overlap: every content block (container, free text, edge label, and every element already on the Board) is checked pairwise before returning; text inside a container is sized from its measured lines plus padding. Arrows are connectors and excluded (see Known limitations).
- All text fits its container: text is measured conservatively (20 px font, 13 px per cell, non-ASCII counts double, hard wrapping of over-long words) and containers are sized from it. Shapes grow for diamond (x2) and ellipse (x1.5) inscribed text.
- Each Step sets a viewport that fits: one `set_viewport` computed for a reference 1200x700 canvas, 40 px margin, zoom 1.0 at most; content needing zoom below 0.25 is refused as `layout_too_large`.
- Long and large fixtures: 300-character unbroken words, 200-character node text and labels, CJK and emoji, 11-spoke map, 24-node chain (refused cleanly), full code walkthroughs, 60 seeded random graphs.

## Contract

- Entry: `layout_lesson_content(content, board_state=None) -> list[operation dict]`. New content is placed below everything already on the Board (a `LAYOUT_SECTION_GAP` band), starting at the leftmost existing x; an empty Board starts at 0,0.
- Errors (`LayoutError`, a `BoardOperationError`): `invalid_layout_content`, `layout_too_large`, `layout_unfit`. Nothing is partially returned.
- Element ids are provisional (`node-1`, `text-1`, `arrow-1`, `label-1`, `line-1`, `panel-1`, `code-1`, `note-1`); the validator allocates the final `ai:<stepId>:<n>` ids.
- Cycles: back edges found by DFS are treated as reversed for layering, so loops do not break the layers.
- All limits are named in `core/limits.py` (`LAYOUT_*`).

## Interface assumptions Story 3.6 must honour

- The 3.2 schema has no `points`; an arrow is an element of the arrow's length, height 1, rotated by `angle` about its centre. The frontend adapter must create arrows as `[[0,0],[width,height]]` and apply `angle` (or the schema gains `points`).
- Viewport `x`,`y` are Excalidraw `scrollX`,`scrollY` (screen = (scene + scroll) x zoom); the canvas size is assumed 1200x700, so the real canvas may show more or less.
- Text uses Excalidraw's default font size (20); the schema cannot carry a font size.

## Known limitations (logged in deferred-work.md)

- A back edge draws on top of its forward edge, and a long edge can cross an unrelated box, because arrows are straight lines.
- No crossing minimisation (in-layer order is input order).
- Real Excalidraw glyph widths were not measured in a browser; the 0.65 em cell is a conservative estimate.

## Verification

- `python -m pytest tests/test_layout.py -q` -- 48 passed. Mutation checks: GAP_X negative fails 15 tests; the label-gap defect (60-character label in a 90 px gap) was found by the tests and fixed.
- `python -m pytest -q` -- 386 passed (1 live test deselected). `python -m ruff check .` clean.
- Self-review only so far: no independent reviewer has run on this story (3.2 had one and it found a real crash); a review pass is still recommended before Story 3.5 builds on it.
