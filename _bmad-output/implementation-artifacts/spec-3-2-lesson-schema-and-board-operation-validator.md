---
title: 'Story 3.2: Lesson schema and Board Operation validator'
type: 'feature'
created: '2026-10-30'
status: 'done'
baseline_commit: '77b2298e8cd846b90b98e93f050f8b97ed7adafa'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-Solvely.ai-2026-10-27/ARCHITECTURE-SPINE.md'
  - '{project-root}/_bmad-output/planning-artifacts/epics.md'
  - '{project-root}/apps/api/core/limits.py'
  - '{project-root}/apps/api/lessons/board.py'
---

<frozen-after-approval reason="human-owned intent; approved Story 3.2 contract transcribed from the existing conversation approval baseline">

## Intent

**Problem:** Epic 3 must prevent malformed or unsafe provider output from reaching the Board.

**Approach:** Add a versioned, framework-free LessonStep schema and a strict atomic Board Operation validator. Validate provider output against fixed limits, preserve strict ownership boundaries, normalize valid operations to AI origin, and allocate final AI element ids on the server.

## Boundaries & Constraints

**Always:** Implement the versioned LessonStep schema and the closed Board Operation vocabulary `add_element`, `update_element`, `remove_element`, `highlight_element`, and `set_viewport`. Use stable typed validation errors. Reject the complete output atomically for unknown operations, non-finite or out-of-range coordinates and geometry, oversized text, invalid colours, operation or target-count limits, and operations targeting learner elements. Keep provider-created element types outside `frame`. Convert valid output to AI-origin operations with server-assigned ids namespaced as `ai:<stepId>:<n>`. Use two-phase provisional ID validation followed by final server ID allocation: provider output may use provisional ids only for validation; the returned operations never expose or depend on provider-selected final ids. Validate earlier-Step AI ownership against the original Step ID namespace rather than the provider-visible current namespace. Pass the server-generated Step UUID through the existing ProviderRequest context and require a provider echo of that exact Step UUID. Existing provider-request context is the only channel for this value; no new client-visible request field is required.

Use approved fixed domain limits, the existing Board coordinate/text/colour conventions, AI origin normalization, and immutable input where an immutable model is appropriate. Domain code imports only stdlib and pydantic. Tests must cover long text, large diagrams, repeated operations, partial operations, malformed ids, ownership namespace mismatches, echoed Step-id mismatches, and frame rejection. A valid final result must preserve original operation semantics except for server-owned ids and AI origin.

**Never:** Never permit raw Excalidraw payloads, arbitrary HTML/JS, provider-selected final ids, provider-created `frame` elements, learner mutation, partial acceptance, Django or SDK imports in domain code, broadening Story 3.2 into generation orchestration, persistence, layout, charging, or endpoint delivery.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|---|---|---|---|
| Valid step | Valid schema, operations, board state and exact Step UUID | Whole step accepted with AI operations and server ids | N/A |
| Unknown operation | Operation outside the closed vocabulary | Entire result rejected | Typed validation error, retryable if provider output |
| Invalid geometry | Coordinates or dimensions outside limits or non-finite | Entire result rejected | Typed validation error |
| Oversized content | Text beyond fixed limit or diagram/count beyond limits | Entire result rejected | Typed validation error |
| Invalid colour | Colour outside approved syntax or palette rules | Entire result rejected | Typed validation error |
| Learner target | Operation removes, updates, highlights, or otherwise targets learner content | Entire result rejected | Typed validation error |
| Earlier-Step target | Earlier AI element addressed using wrong or current namespace | Entire result rejected | Ownership validation uses original Step ID |
| Provisional id | Valid provider provisional id in add/update sequence | Provisional ids validate, then final `ai:<stepId>:<n>` ids are allocated | No provider final id accepted |
| Step UUID echo | Provider output omits, echoes another value, or mismatches exact generated UUID | Entire result rejected | Typed validation error |
| Frame provider element | Provider add-element requests `frame` | Entire result rejected | Provider types exclude `frame` |
| Repeated/partial operations | Repeated or incomplete operation sequences | Entire result rejected rather than partially applying | Typed validation error |

</frozen-after-approval>

## Open Questions

None. The existing Story 3.2 approval baseline is frozen; the four explicit corrections and acceptance criteria above resolve the contract.

## Code Map

- `apps/api/core/limits.py` -- fixed board and AI limits to reuse or extend with Story 3.2 domain caps.
- `apps/api/lessons/board.py` -- existing strict board validation and element/geometry conventions.
- `apps/api/ai/ports.py` -- existing ProviderRequest context that must carry the server-generated Step UUID.
- `apps/api/ai/errors.py` -- typed provider and output errors; reuse the established error boundary.
- `apps/api/domain/` -- framework-free Story 3.2 schema and validator boundary with no Django or provider imports.
- `apps/api/tests` -- Story 3.2 unit and fixture coverage.

## Tasks & Acceptance

**Execution:**
- [x] `apps/api/core/limits.py` -- add fixed Story 3.2 operation, target, provisional-id, text and provider element-type limits while reusing approved Board limits.
- [x] `apps/api/domain/` -- implement the versioned LessonStep and closed Board Operation models with strict unknown-field rejection.
- [x] `apps/api/domain/` -- implement two-pass provisional-ID validation and final server ID allocation.
- [x] `apps/api/domain/` -- validate operations against Board state using origin and Step ID ownership, with the original earlier-Step namespace.
- [x] `apps/api/ai/ports.py` -- extend ProviderRequest context with the server-generated Step UUID when approved by the existing contract.
- [x] `apps/api/tests/test_lesson_schema.py` and fixture tests -- cover valid and rejected output, ownership, ID namespace and AI normalization.

**Acceptance Criteria:**
- Given versioned provider output, when it contains an unknown operation, invalid geometry, oversized text, invalid colour, excess operations/targets, a learner target, or `frame`, then the whole output is rejected with a typed error.
- Given valid provider output with provisional ids, when validation succeeds, then returned operations carry server ids `ai:<stepId>:<n>` and AI-origin metadata.
- Given earlier-Step AI elements, when ownership is checked, then validation uses each original Step ID namespace and rejects namespace mismatch.
- Given a server-generated Step UUID in ProviderRequest context, when provider output is validated, then omission or any mismatched echo is rejected.
- Given repeated, partial, long-text or large-diagram fixtures, when normalized, then outputs are rejected without partial application.

## Implementation Notes

Implementation approval baseline: user explicitly approved the existing Story 3.2 technical contract, including the four corrections and scope limits, so no additional human checkpoint is required.

## Spec Change Log

## Review Triage Log

| verdict | finding | evidence |
|---|---|---|
| patch | Forward provisional references could leak provider ids. | Precomputed final ID mapping now normalizes references regardless of operation order. |
| patch | Viewport, zoom and opacity accepted invalid values. | Strict bounded model validators and normalized change checks were added and covered. |
| patch | Unowned AI elements and post-removal operations could pass ownership validation. | Added explicit unowned ownership rejection and remove-then-target guard. |

## Design Notes

Use provider provisional references only to connect operations within one result; allocate final ids only after every operation has passed. Evaluate ownership against the Board element's immutable origin and Step namespace before normalization. Never mutate learner elements or Board state until whole validation succeeds.

## Verification

**Commands:**
- `python -m pytest tests/test_lesson_schema.py -q` -- expected: Story 3.2 tests pass, including every matrix row.
- `python -m pytest -q` -- expected: full backend suite passes.
- `python -m ruff check ai lessons core tests` -- expected: no lint errors.

## Orchestrator Review (2026-11-06)

- Provenance: implemented by the VS Code agent (session 44a49d78, 2026-10-30 14:50 to 16:22) after a planning session (c4d401e9, 13:47 to 14:46) that changed no files; the spec's approval note is consistent with that. Git checkpoint refs under `refs/agents/` hold both sessions.
- Independently re-run: backend pytest 338 passed (1 live test deselected), ruff clean, `makemigrations --check` clean, spectacular `--fail-on-warn` exit 0. No API key anywhere in the repo or its history (scanned values, counts only).
- DEFECT FOUND AND FIXED: every valid LessonStep containing a `set_viewport` operation crashed with `AttributeError` (the validator called `_target(op)` on an operation that has no element id), which would have been a 500 on any lesson that sets the view. The 15 original tests only covered invalid viewports, which pydantic rejects before the buggy loop. Fixed in `domain/board_operations.py` (viewport skips target lookup and normalisation of targets); 4 regression tests added; mutation check (fix removed) fails all 4, restored passes.
- HARDENING: `ProviderRequest.step_id` is appended to the trusted system instruction by the Gemini adapter but was only `min_length=1`; it must now parse as a UUID (normalised to canonical form) so free text can never reach the system instruction; 2 tests added.
- CLEANUP: the hardcoded `20_000` text limits in the domain now use `limits.LESSON_ELEMENT_TEXT_MAX_LENGTH`.
- Accepted: domain code imports `core.limits` (a constants-only module) besides the standard library and pydantic, a small relaxation of AD-1's wording; ports.py now also imports stdlib `uuid`.
