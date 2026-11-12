# RESUME HERE (last updated 2026-10-29, Epic 1 complete)

Read this first in a new session, then `docs/PROJECT_CONTEXT.md`.

## What the project is
Whiteboard Tutor (repo folder `Solvely.ai`): free, whiteboard-first AI tutor for adults 18+ (college + IT/programming). Django/DRF + PostgreSQL backend, React/TS/Vite + Excalidraw frontend (not started), Gemini via `google-genai` (backend only). Workflow: BMAD Method.

## Rules from the user (standing)
- Commits: Claude commits locally on `push-queue` only; pushes happen via `scripts/push-day.sh` when the user asks (policy changed 2026-10-29, see Git state). Never add Claude as co-author.
- Decide autonomously; ask only when truly necessary. Model rule (user, 2026-10-29): use Sonnet subagents for routine work; Opus only for main operations (security/architecture-critical, AI pipeline, design-heavy). Set `model` explicitly on every Agent call. End every message with a line saying whether background work is in progress.
- Memory notes also saved in `~/.claude/projects/.../memory/`.

## Done and verified
| Item | Where | Evidence |
|---|---|---|
| Backend foundation | `apps/api` | health/ready, request-ID, OpenAPI |
| PostgreSQL 18.6 local, db `tutor`, app role | credentials only in git-ignored `apps/api/.env` | migrations applied, tests run on PostgreSQL |
| BMAD installed (v6.12.4, `bmm`, claude-code) | `_bmad/`, `.claude/skills/` | 29 skills |
| Product brief | `_bmad-output/planning-artifacts/briefs/brief-Solvely.ai-2026-10-27/` | status complete |
| PRD (FR-1..FR-18) | `_bmad-output/planning-artifacts/prds/prd-Solvely.ai-2026-10-27/prd.md` | status final |
| Architecture spine (AD-1..AD-12) | `_bmad-output/planning-artifacts/architecture/architecture-Solvely.ai-2026-10-27/` | lint_spine ok |
| Epics (7 epics, 29 stories) | `_bmad-output/planning-artifacts/epics.md` | FR1-18 covered |
| Sprint tracking | `_bmad-output/implementation-artifacts/sprint-status.yaml` | all backlog except below |

## Completed stories (verified)
- Story 1.2 registration + 18+ confirmation: done (25 tests at the time).
- Story 1.3 sign in/out/me + password reset: done.
- Story 1.4 owner-scoped base (OwnedModel, owned viewset, isolation harness): done.
- Story 1.5 account deletion: done. Full suite: 105 passed in ~5 s, ruff clean, no migration drift.
- Story 1.1 web shell + typed API client + design tokens: done (web: lint/typecheck/24 tests/build pass; TypeScript 5.9.3 pinned).
- Story 1.7 auth screens (sign-up, sign-in, forgot/reset, guards, sign out): done; web 52 tests pass; live browser e2e passed.
- Story 2.2 board tools: learner origin tagging, zoom/fit controls, self-hosted fonts: done and queued (web 94 tests).
- Story 2.1 Lesson model/API + New lesson + lazy Excalidraw Board: done and queued (9 commits on push-queue, not pushed). Web 73 tests, backend 138 tests.
- Story 1.6 theme preference + settings page + delete-account dialog (POST /auth/account/delete/): done. Web 61 tests, backend 116 tests, all green.
- EPIC 1 IS COMPLETE (stories 1.1 to 1.7).
- Sprint file: `_bmad-output/implementation-artifacts/sprint-status.yaml` (1.2, 1.3 = done; epic-1 in-progress).

## Git state (CHANGED 2026-10-29: do NOT push directly)
- Remote: https://github.com/AbdullahAnwar26/Solvely.ai.git. Author for commits: AbdullahAnwar26 <abdullahanwar264@gmail.com> (repo-local config). No Co-Authored-By lines.
- `main` = what is on GitHub (head `efc860b`, Epic 1 complete). It only moves when the user asks to run the daily replay.
- Development happens on the local branch **`push-queue`** (currently checked out). Finished, verified work is committed there as small logical commits and is NOT pushed.
- Each day: `bash scripts/push-day.sh <N>` replays the next N queued commits onto `main` with the real current date and pushes. Details, queue and the 21-day calendar are in `docs/PUSH_PLAN.md`.
- After every finished major part Claude must: commit it on `push-queue`, update the Queue and Calendar tables in `docs/PUSH_PLAN.md`, and not push unless asked. Reason: GitHub's graph uses commit creation date, and the user wants commits spread over days.
- Never fake or edit commit dates.

## Remaining work (in order)
1. Continue Epic 2: Story 2.3 (autosave with BoardRevision + 409 conflict, AD-4; security/concurrency-sensitive: use Opus), then 2.4 (resume and recovery). UX contract is FINAL (`_bmad-output/planning-artifacts/ux-designs/ux-Solvely.ai-2026-10-28/`, 28 UX-DRs). OpenAPI schema is clean. Web commands from repo root: `npm ci`, `npm run lint|typecheck|test|build`, `npm run gen:api` (needs API on :8000).
3. (Done 2026-10-29) `bmad-ux` produced DESIGN.md + EXPERIENCE.md; user chose calm study-room tone and follow-device theme. Epics now 31 stories (added 1.6 theme/settings, 4.5 shortcuts dialog).
4. Story 1.1 (web shell, Vite/React/TS; check TypeScript 7 toolchain compatibility before pinning), then Epic 2 to Epic 7 per `epics.md`.
5. Epic 7.3 needs Docker.

## Open items / blockers
- Docker Desktop engine returned HTTP 500 on last check; user must look at the Docker Desktop window (WSL2/first-run). Not needed until Story 7.3.
- Unverified: Solvely's real pricing/whiteboard; Gemini model id and paid price; success-metric targets (all `[ASSUMPTION]`); daily allowance (assumed 5/day).
- Product name undecided (working title Whiteboard Tutor).
- Commit/push policy changed by the user on 2026-10-28: Claude may commit and push to the repo above (see Git state).

## How to resume
Environment: Windows, PowerShell/Bash. `uv` is `python -m uv` (installed with `pip install --user uv`).

```
cd C:\Users\Windows11\Desktop\Solvely.ai\apps\api
.venv\Scripts\python -m pytest -q
.venv\Scripts\python -m ruff check .
.venv\Scripts\python manage.py makemigrations --check
```
Postgres service `postgresql-x64-18` must be running (it auto-starts). `apps/api/.env` holds `DATABASE_URL`.

To continue, tell Claude: "Resume from docs/RESUME.md and build Story 2.3, committing on push-queue and updating docs/PUSH_PLAN.md (do not push)." The `bmad-build` workflow is regenerated by running:
`python -m uv run --no-cache "C:/Users/Windows11/Desktop/Solvely.ai/_bmad/scripts/render_skill.py" --project-root "C:/Users/Windows11/Desktop/Solvely.ai" --skill "C:/Users/Windows11/Desktop/Solvely.ai/.claude/skills/bmad-build"`

## Security note
The postgres superuser password was typed in chat once to create the app role; it is not stored in any file. Consider changing it (`ALTER USER postgres PASSWORD ...`) since it appeared in the conversation transcript.
