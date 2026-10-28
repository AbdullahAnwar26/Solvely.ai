> **Checkpoint: see docs/RESUME.md for the exact resume point (Story 1.2 in progress).**

# Project Context (verified)

Last updated: 2026-10-27

## Repository state
- Started from an EMPTY directory (`Solvely.ai`), not a git repo. `git init` performed in Phase 0.
- No pre-existing code, docs, or data to preserve.

## Local environment (verified by command)
| Tool | Status |
|---|---|
| Node | v24.22.1, npm 11.19.1 (pnpm not installed; npm workspaces used) |
| Python | 3.13.15 |
| Git | 2.56 |
| Docker CLI | 29.9.2 installed, **daemon NOT running** (engine pipe missing) |
| PostgreSQL / psql | **not installed** |
| Redis | not installed (not needed yet; no justified background work) |
| RAM | ~8 GB target (per requirements) |

## Latest versions seen on registries (2026-10-27)
Django 6.1.2, DRF 3.18.3, drf-spectacular 0.30.0, google-genai 2.33.0, psycopg 3.3.6,
pytest-django 4.14.0, gunicorn 26.2.0, pydantic 2.14.1, ruff 0.17.3, mypy 2.4.0,
React 19.3.1, Vite 8.3.5, @excalidraw/excalidraw 0.18.1, Vitest 5.0.5, TypeScript 7.0.2.
Compatibility (e.g. Excalidraw 0.18 peer range vs React 19) must be verified at install time, not assumed.

## Workflow: BMAD Method
- Installed `bmad-method@6.12.4` (module `bmm`, tool `claude-code`) into `_bmad/`; 29 skills in `.claude/skills/`; artifacts go to `_bmad-output/`.
- Planning flow: `bmad-product-brief` -> `bmad-prd` -> `bmad-ux` -> `bmad-architecture` -> `bmad-create-epics-and-stories` -> `bmad-sprint-planning` -> `bmad-agent-dev` / `bmad-build`.
- `bmad-build` / `bmad-build-auto` need `uv` (not installed yet).
- The Phase table in IMPLEMENTATION_PLAN.md is the working outline; BMAD epics/stories should supersede it once generated.

## Key decisions
- npm workspaces monorepo: `apps/web`, `apps/api`(Python), `packages/shared`.
- Database config is `DATABASE_URL`-driven. Production/dev target is PostgreSQL.
  Because no Postgres is available locally and Docker is stopped, unit tests may run against SQLite
  until Postgres is available; Postgres-specific verification is tracked as an open item.
- Gemini only via backend `google-genai`; model id from env `GEMINI_MODEL`.

## Current implementation status
- Phase 0: done (docs, BMAD install).
- BMAD planning DONE (2026-10-27): brief, PRD (18 FRs), architecture spine (AD-1..AD-12), epics.md (7 epics, 29 stories), sprint-status.yaml (all backlog). Planning artifacts in `_bmad-output/planning-artifacts/`, tracking in `_bmad-output/implementation-artifacts/sprint-status.yaml`. UX contract (`bmad-ux`) NOT yet produced: readiness verdict CONCERNS; run it before UI stories (1.1, 2.2, 3.6).
- Audience/cost decisions: v1 adults 18+ only (Gemini terms), free daily Lesson Allowance on paid Gemini tier.
- Local DB: PostgreSQL 18.6 service running, db `tutor`, app role in git-ignored `apps/api/.env`. Docker Desktop engine returned HTTP 500 on last check (unresolved).
- `uv` installed via `python -m pip install --user uv` (invoke as `python -m uv`).
- Phase 1 (partial): backend skeleton in `apps/api` (Django 6.1.2, DRF, health/ready, request IDs, OpenAPI). `pytest` 4 passed, `ruff` clean (SQLite, venv at `apps/api/.venv`).
- Phase 1 remaining: Vite/React/TS app in `apps/web`, `packages/shared`, CI, Docker Compose, Postgres verification.
- Phases 2-10: not started.
- Resume backend checks: `cd apps/api && .venv/Scripts/python -m pytest -q && .venv/Scripts/python -m ruff check .`

## Open blockers / decisions
1. Docker Desktop daemon must be started (or Postgres installed) to verify migrations on PostgreSQL.
2. A `GEMINI_API_KEY` is needed only for optional live-provider tests; automated tests use mocks.
