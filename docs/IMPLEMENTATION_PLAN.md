# Implementation Plan

Status legend: [ ] not started, [~] in progress, [x] done and verified.

| Phase | Scope | Acceptance criteria | Status |
|---|---|---|---|
| 0 | Inspection, context, plan | PROJECT_CONTEXT + this plan reflect verified facts | [~] |
| 1 | Foundation: monorepo, Django+DRF API skeleton, health/readiness, settings per env, Vite+React+TS strict app, lint/type/test tooling, CI | `pytest`, `ruff`, web `tsc`, `vitest`, `vite build` all pass from documented commands | [ ] |
| 2 | App shell, routing, design system, workspace layout, empty/error/loading states | Routes render; responsive layout tested | [ ] |
| 3 | Excalidraw board, serialization, revisioned snapshots, optimistic concurrency | Board edits persist/restore; stale save rejected (409) | [ ] |
| 4 | Gemini provider interface, schema-validated lesson/operations, orchestrator, mocked tests | Malformed AI output rejected; valid output yields safe board ops | [ ] |
| 5 | End-to-end learning flow (explain/solve/hint/simplify/follow-up), step navigation | Playwright journey with mocked Gemini | [ ] |
| 6 | Lesson management, search, summaries, practice, notes | Lessons CRUD/search/resume | [ ] |
| 7 | Accounts, session auth + CSRF, object-level authz | Cross-user access test returns 404/403 | [ ] |
| 8 | Hardening: failure injection, a11y, limits, risk register | Documented risk register; tests pass | [ ] |
| 9 | Docker, prod config, CI, backup/restore, deploy docs | Images build; migrations on clean Postgres | [ ] |
| 10 | Final verification, go/no-go | Full suite green; limitations documented | [ ] |

## Dependencies / ordering constraints
- Phase 3 snapshot model precedes Phase 4 (AI ops apply to revisioned board).
- Ownership fields (`owner` FK) are included from the first lesson model, auth enforced in Phase 7
  (before any public deployment).
- Postgres verification (Phase 1/9) is gated on Docker or a local Postgres being available.

## First slice (Phase 1)
Backend: Django project `config`, `core` app with `/api/v1/health/` and `/api/v1/ready/`, request-ID middleware,
env-driven settings, DRF + OpenAPI schema endpoint, pytest tests.
Frontend: Vite React TS strict app with a Vitest smoke test.
