---
status: draft
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-Solvely.ai-2026-10-27/prd.md
  - _bmad-output/planning-artifacts/architecture/architecture-Solvely.ai-2026-10-27/ARCHITECTURE-SPINE.md
  - _bmad-output/planning-artifacts/briefs/brief-Solvely.ai-2026-10-27/brief.md
---

# Whiteboard Tutor - Epic Breakdown

## Overview

Epics and stories for Whiteboard Tutor v1 (adults 18+, free daily Lesson Allowance), decomposed from the PRD and the architecture spine (AD-1 to AD-12). No UX design contract exists yet (`bmad-ux` not run); UX requirements below come from the PRD and are refined when UX is produced. The backend foundation already exists in `apps/api` (Django 6.1.2, DRF, health/ready, request-ID middleware, pytest on PostgreSQL); the web app does not exist yet.

## Requirements Inventory

### Functional Requirements

- FR1: Interactive Board: draw, select, move, resize, delete, zoom, pan, fit, undo/redo; persists; Learner Content distinguishable from AI Content.
- FR2: Teaching request with Teaching Mode produces a Lesson with Steps; length limit and allowance refusal.
- FR3: Step-by-step delivery: play, pause, resume, restart, jump; keyboard reachable.
- FR4: Follow-up tied to the current Step; no whole-Lesson regeneration; Learner Content survives.
- FR5: Math typeset and copyable; code in copyable blocks; deterministically computed results marked verified.
- FR6: AI output accepted only if schema- and limit-valid; bounded retries; no fabricated fallback.
- FR7: Teaching Modes: Explain, Solve, Hint, Simplify (Practice via FR13; Check Understanding deferred).
- FR8: Readable, non-overlapping generated layout for sequential, flowchart, concept-map, code-walkthrough content.
- FR9: Cancel a generation; failed/interrupted generation leaves Lesson and Board intact.
- FR10: Autosave and resume at same Step; 409 on stale save; visible save status.
- FR11: Lesson library: list, search, filter, rename, duplicate, archive, delete.
- FR12: Export Board image and Lesson file.
- FR13: Practice questions linked to a Lesson, answers, explanations, stored attempts.
- FR14: Personal notes per Step and Lesson summary with key takeaways.
- FR15: Registration with 18+ confirmation, secure sessions, password reset by email.
- FR16: Learner can only access their own data.
- FR17: Free daily Lesson Allowance with visible remaining/reset and global ceiling.
- FR18: Account and data deletion; privacy notice naming AI provider processing.

### NonFunctional Requirements

- NFR1: First Step visible within 10 s p90 under normal load [ASSUMPTION]; smooth Board to ~500 elements on an 8 GB laptop [ASSUMPTION].
- NFR2: Security: object-level authz, rate limits on AI and auth endpoints, secrets never in browser, untrusted input/output handling, no stack traces.
- NFR3: Accessibility: keyboard, visible focus, reduced motion, WCAG 2.2 AA target for core flows; light/dark themes.
- NFR4: Reliability: explicit timeouts, bounded retries, health/readiness, recoverable save failures.
- NFR5: Responsive layouts reorganise on laptop, tablet, mobile.
- NFR6: Privacy: no prompts or student content in logs by default.
- NFR7: Cost: per-Learner and global limits; usage accounting per request.

### Additional Requirements

- AR1: Domain code is framework-free; `google.genai` only in `ai/providers/gemini.py` (AD-1).
- AR2: Board Operation closed vocabulary, server-side validation, single frontend adapter (AD-2).
- AR3: Element `customData.origin` and `stepId`; AI ids namespaced `ai:<stepId>:<n>` (AD-3).
- AR4: Append-only `BoardRevision` with optimistic concurrency (AD-4).
- AR5: Owner-scoped managers on every owned model (AD-5).
- AR6: Session cookie + CSRF, same-origin production (AD-6).
- AR7: Charge allowance before provider call, refund on failure, bounded concurrency, no queue (AD-7).
- AR8: Plan-then-step generation (AD-8); prompts and schemas versioned (AD-9); verified computation (AD-10); typed errors (AD-11).
- AR9: FakeProvider for all automated tests; live tests marked and excluded (AD-12).
- AR10: Single error envelope, `/api/v1/`, OpenAPI as contract, client types generated from it.
- AR11: Stack pins per spine; TypeScript major pinned only after toolchain check; Gemini model id from `GEMINI_MODEL`.
- AR12: Deployment: one container (gunicorn gthread + whitenoise), PostgreSQL, secrets from platform, `pg_dump` backups, CI for lint/type/test/build.

### UX Design Requirements

None yet (no UX contract). Epic 7 includes a story to reconcile with the UX contract once `bmad-ux` is run.

### FR Coverage Map

FR1: Epic 2. FR2: Epic 3. FR3: Epic 3. FR4: Epic 4. FR5: Epic 4. FR6: Epic 3. FR7: Epic 3 (Explain, Solve), Epic 4 (Hint, Simplify). FR8: Epic 3. FR9: Epic 4. FR10: Epic 2. FR11: Epic 6. FR12: Epic 6. FR13: Epic 5. FR14: Epic 5. FR15: Epic 1. FR16: Epic 1. FR17: Epic 3. FR18: Epic 1 (deletion), Epic 7 (privacy notice finalised).

## Epic List

### Epic 1: Accounts and a Private Learning Space
A Learner can register (18+), sign in, reset a password, use the app inside a responsive shell, see only their own data, and delete their account.
**FRs covered:** FR15, FR16, FR18. Also stands up the web app.

### Epic 2: Editable Whiteboard Lessons
A Learner can start a Lesson, draw and edit on a Board, and have it autosave and resume exactly, with no AI.
**FRs covered:** FR1, FR10.

### Epic 3: Taught on the Board (Explain and Solve)
A Learner asks a question and watches a Lesson taught step by step on the Board, within a free daily allowance.
**FRs covered:** FR2, FR3, FR6, FR7 (Explain, Solve), FR8, FR17.

### Epic 4: Interactive Tutoring
A Learner can ask follow-ups, get Hints or Simplify a Step, cancel or retry a generation, and see math and code clearly with verified results marked.
**FRs covered:** FR4, FR5, FR7 (Hint, Simplify), FR9.

### Epic 5: Practice, Notes and Summaries
A Learner can practise a Lesson's concepts, keep notes on Steps, and get a summary.
**FRs covered:** FR13, FR14.

### Epic 6: Lesson Library and Export
A Learner can find, organise and export their Lessons.
**FRs covered:** FR11, FR12.

### Epic 7: Ready for Public Launch
The product is hardened, accessible, deployable and legally ready for real users.
**FRs covered:** FR18 (notice), NFR1 to NFR7 verification.

## Epic 1: Accounts and a Private Learning Space

Learners can safely sign up and keep their work private.

### Story 1.1: Web app shell and API client
As a Learner, I want to open the app and see a navigable, responsive shell, so that I can reach every feature from one place.
**Acceptance Criteria:**
**Given** the web app is built **When** I open `/` **Then** a shell with sidebar, "New lesson" action and content area renders on laptop, tablet and phone widths.
**And** the SPA is a React 19 + TypeScript strict + Vite app in `apps/web` with lint, type-check, Vitest and build commands passing.
**And** an API client generated from the OpenAPI schema is used and a dev proxy reaches `/api/v1/health/`.
**And** the layout is operable by keyboard with visible focus.

### Story 1.2: Registration with 18+ confirmation
As a new Learner, I want to register with email and password and confirm I am 18+, so that I can use the tutor.
**Acceptance Criteria:**
**Given** the registration form **When** I submit without the 18+ box **Then** the API returns a validation error and no account is created.
**Given** valid data **When** I register **Then** a user and profile exist, the 18+ confirmation timestamp is stored, and I am signed in via a session cookie (HttpOnly, SameSite=Lax; Secure in production).
**And** duplicate emails and weak passwords are rejected with the error envelope.
**And** registration is rate limited.

### Story 1.3: Sign in, sign out, password reset
As a Learner, I want to sign in, sign out and reset my password, so that I can return securely.
**Acceptance Criteria:**
**Given** valid credentials **When** I sign in **Then** I get a session and CSRF is enforced on unsafe requests.
**Given** I sign out **Then** the session is invalidated server-side.
**Given** I request a reset **Then** an email is sent through the configured backend, the link is single-use and expires, and the response never reveals whether the email exists.
**And** login attempts are throttled.

### Story 1.4: Owner-scoped data foundation
As a Learner, I want my data isolated, so that no one else can see my Lessons.
**Acceptance Criteria:**
**Given** the shared `OwnedModel` base and `for_user()` manager **When** a view queries owned objects **Then** only the requester's rows are returned.
**Given** user A requests user B's object id **Then** the API returns 404.
**And** a test suite proves cross-user reads, updates and deletes fail for every owned endpoint that exists, and new endpoints must register in it.

### Story 1.5: Account deletion
As a Learner, I want to delete my account and all my data, so that I control my information.
**Acceptance Criteria:**
**Given** I confirm deletion with my password **When** it completes **Then** my user and all owned records are removed in one transaction.
**And** subsequent requests with my old session fail.
**And** a test verifies no orphaned rows remain.

## Epic 2: Editable Whiteboard Lessons

Learners can create and edit a Board that persists reliably.

### Story 2.1: Create and open a Lesson with an empty Board
As a Learner, I want to start a new Lesson, so that I have a Board to work on.
**Acceptance Criteria:**
**Given** I am signed in **When** I click "New lesson" **Then** a Lesson with a title and empty Board revision 0 is created and opened at `/lessons/:id`.
**And** Excalidraw loads lazily, is cleaned up on leave, and works with 0.18.x on React 19.
**And** opening someone else's or a deleted Lesson shows a not-found state.

### Story 2.2: Board editing tools and viewport controls
As a Learner, I want full whiteboard tools, so that I can draw and annotate.
**Acceptance Criteria:**
**Given** the Board **Then** I can draw shapes, arrows, text and freehand; select, move, resize, delete; zoom, pan, fit to content; undo and redo.
**And** new elements carry `customData.origin = "learner"`.
**And** controls are keyboard accessible and responsive at tablet and phone widths.

### Story 2.3: Autosave with revisions and conflict protection
As a Learner, I want my Board saved automatically without losing work, so that I never lose progress.
**Acceptance Criteria:**
**Given** I edit **When** I pause for the debounce interval **Then** the client sends the Board with its base revision and the server stores a new `BoardRevision` (append-only).
**Given** a stale base revision **Then** the server returns 409 with the current revision and the client does not overwrite.
**And** a save-status indicator shows saved, saving, or failed with retry.
**And** the payload is validated for schema version and size limit.

### Story 2.4: Resume after refresh or interruption
As a Learner, I want to reopen a Lesson and see my latest Board, so that I can continue.
**Acceptance Criteria:**
**Given** a saved Lesson **When** I reload or return later **Then** the latest revision loads with the same elements and viewport.
**Given** a failed save followed by reload **Then** the last good revision loads and unsaved local changes are offered for recovery.
**And** an end-to-end test covers edit, reload, verify.

## Epic 3: Taught on the Board (Explain and Solve)

Learners get a real step-by-step lesson drawn on the Board.

### Story 3.1: AI provider port, Gemini adapter and FakeProvider
As a developer, I want a provider interface with a Gemini implementation and a fake, so that teaching logic is testable and portable.
**Acceptance Criteria:**
**Given** the `AIProvider` port **Then** `ai/providers/gemini.py` is the only importer of `google.genai`, reads `GEMINI_API_KEY` and `GEMINI_MODEL` from the environment, applies an explicit timeout and bounded retries.
**And** `FakeProvider` serves fixtures (valid, malformed, oversized, repeated, partial) and all automated tests use it.
**And** a provider diagnostic endpoint reports configured/unconfigured without revealing the key.
**And** missing config returns a typed `provider_unavailable` error, never a fake answer.

### Story 3.2: Lesson schema and Board Operation validator
As a developer, I want strictly validated lesson output, so that unsafe or malformed content never reaches the Board.
**Acceptance Criteria:**
**Given** the versioned `LessonStep` schema **When** output has unknown operation types, out-of-range coordinates, oversized text, bad colours, too many operations or targets a learner element **Then** the whole output is rejected with a typed error.
**And** valid output is converted to AI-origin operations with server-assigned ids `ai:<stepId>:<n>`.
**And** fixture tests cover long text, large diagrams, repeated and partial operations.

### Story 3.3: Deterministic layout engine
As a Learner, I want generated content laid out cleanly, so that nothing overlaps or is clipped.
**Acceptance Criteria:**
**Given** step content of type sequential solution, flowchart, concept map, or code walkthrough **When** laid out **Then** no two elements overlap and all text fits its container using measured or conservative text sizes.
**And** each Step sets a viewport that fits its content.
**And** fixture tests with long and large inputs pass.

### Story 3.4: Daily Lesson Allowance
As a Learner, I want a free daily allowance I can see, so that I know what I can do today.
**Acceptance Criteria:**
**Given** a generation request **When** the Learner has allowance **Then** it is charged in the same transaction as the check, and a `UsageRecord` is written.
**Given** the allowance is exhausted **Then** the request is refused with the reset time and no provider call is made.
**Given** the global daily ceiling is reached **Then** the Learner sees an honest at-capacity message.
**And** provider failure refunds the charge, and the UI shows remaining allowance and reset time.

### Story 3.5: Explain and Solve lesson generation
As a Learner, I want to ask a question and receive a plan and Steps, so that I get taught, not just answered.
**Acceptance Criteria:**
**Given** a request within the length limit and an Explain or Solve mode **When** I submit **Then** a plan call returns Step outlines, then each Step is generated by its own call and persisted with its Board Operations and explanation.
**Given** a malformed result **Then** bounded retries run, then a retryable error shows and the Board is unchanged.
**And** prompts and schemas come from versioned `v1` folders, user text is never placed in system instructions, and prompt-injection fixtures are rejected.
**And** a revision is written only after full validation, in one transaction.

### Story 3.6: Step player on the Board
As a Learner, I want to play, pause and jump between Steps, so that I can learn at my pace.
**Acceptance Criteria:**
**Given** a Lesson with Steps **Then** I can play, pause, resume, restart and jump; each Step applies its operations through the single typed frontend adapter and shows its explanation panel.
**And** jumping to a Step shows that Step's Board state, preserving Learner Content.
**And** controls are keyboard accessible, and the panel reflows below the Board on narrow screens.

## Epic 4: Interactive Tutoring

### Story 4.1: Follow-up questions on the current Step
As a Learner, I want to ask about the Step I'm on, so that confusion is resolved in context.
**Acceptance Criteria:**
**Given** a current Step **When** I ask a follow-up **Then** only the affected Step(s) are regenerated or extended, not the whole Lesson.
**And** Learner Content is untouched by the update.
**And** the exchange is stored in Lesson history.

### Story 4.2: Hint and Simplify modes
As a Learner, I want progressive hints and simpler re-explanations, so that I can work it out myself.
**Acceptance Criteria:**
**Given** Hint **Then** each request reveals more without stating the final answer first, and hint level is tracked.
**Given** Simplify **Then** only the current Step is rewritten at lower complexity.
**And** FakeProvider fixtures verify both behaviours.

### Story 4.3: Cancel, retry and recover generations
As a Learner, I want to cancel or retry a generation safely, so that failures never wreck my Lesson.
**Acceptance Criteria:**
**Given** a running generation **When** I cancel **Then** the request aborts, the allowance is refunded and the Board is unchanged.
**Given** provider timeout, rate limit, or invalid output **Then** a typed error with `retryable` is shown and retry works.
**And** tests inject each failure and assert no revision was written.

### Story 4.4: Math and code rendering with verified marks
As a Learner, I want clear equations and code, and to know what was actually verified.
**Acceptance Criteria:**
**Given** an equation **Then** it renders typeset and its source is copyable; code appears in a copyable monospace block.
**Given** arithmetic or algebra that the deterministic evaluator confirms **Then** it shows a verified marker; unconfirmed claims show none.
**And** evaluator mismatches with the model result are flagged, not hidden.

## Epic 5: Practice, Notes and Summaries

### Story 5.1: Practice questions and attempts
As a Learner, I want practice questions on a Lesson, so that I can test my understanding.
**Acceptance Criteria:**
**Given** a Lesson **When** I request practice **Then** validated questions linked to its concepts are generated (allowance charged) and shown.
**Given** I answer **Then** the attempt is stored and an explanation is shown.
**And** questions and attempts are owner-scoped.

### Story 5.2: Step notes
As a Learner, I want personal notes on Steps, so that I can capture my own understanding.
**Acceptance Criteria:**
**Given** a Step **Then** I can add, edit and delete notes that persist with the Lesson and are owner-scoped.

### Story 5.3: Lesson summary and key takeaways
As a Learner, I want a summary of a Lesson, so that I can revise quickly.
**Acceptance Criteria:**
**Given** a completed Lesson **When** I request a summary **Then** a validated summary with key takeaways is generated, stored, and shown (allowance charged).
**And** failure leaves the Lesson intact with a retry.

## Epic 6: Lesson Library and Export

### Story 6.1: List, search and filter Lessons
As a Learner, I want to find my Lessons, so that I can resume them.
**Acceptance Criteria:**
**Given** my Lessons **Then** the library lists them paginated, newest first, with search by title and filters (mode, archived).
**And** a useful empty state shows for new users, and queries avoid N+1 patterns (tested).

### Story 6.2: Rename, duplicate, archive, delete
As a Learner, I want to manage Lessons, so that my library stays tidy.
**Acceptance Criteria:**
**Given** a Lesson **Then** I can rename, duplicate (copying Steps and latest Board), archive and restore, or delete after confirmation.
**Given** a deleted Lesson **Then** it returns not-found and its data is removed.

### Story 6.3: Export Board and Lesson
As a Learner, I want to export my work, so that I can keep or share it.
**Acceptance Criteria:**
**Given** a Board **Then** I can export an image (PNG or SVG) and a Lesson file (versioned JSON that re-imports validated).
**And** invalid or oversized imports are rejected with the error envelope.

## Epic 7: Ready for Public Launch

### Story 7.1: Failure-injection and security hardening
As the operator, I want proven safe behaviour under failure and abuse, so that launch is low-risk.
**Acceptance Criteria:**
**Given** malformed AI output, provider outage, quota exhaustion, oversized requests and stale saves **Then** each has a passing automated test and no data corruption.
**And** rate limits, security headers, `DEBUG=False`, secure cookies and `pip` / `npm` vulnerability checks are verified, with a documented risk register.

### Story 7.2: Accessibility and responsive verification
As a Learner with accessibility needs, I want core flows usable by keyboard and screen reader, so that I'm not excluded.
**Acceptance Criteria:**
**Given** register, create Lesson, ask, play Steps and save **Then** each works by keyboard with visible focus, honours reduced motion, and meets WCAG 2.2 AA checks on contrast and labels, in light and dark themes.
**And** layouts are verified at laptop, tablet and phone widths.

### Story 7.3: Production packaging and CI
As the operator, I want reproducible builds and deploys, so that I can ship safely.
**Acceptance Criteria:**
**Given** the repo **Then** CI runs lint, type-check, tests and builds for api and web, and a Dockerfile builds one image served by gunicorn gthread + whitenoise.
**And** migrations pass on a clean PostgreSQL, `/health` and `/ready` work, backup/restore and rollback steps are documented and the restore is rehearsed.
**And** no secrets are in images or the repo.

### Story 7.4: Privacy notice and end-to-end acceptance
As a Learner, I want to know how my data is used, and the product must prove its core journey.
**Acceptance Criteria:**
**Given** the app **Then** a privacy notice names that prompts go to the AI provider and describes deletion and retention.
**And** a Playwright journey with FakeProvider covers register, create Lesson, ask, edit Board, follow-up, save, reopen, second user denied, AI failure recovery.
**And** any UX contract produced by `bmad-ux` is reconciled into stories before release.

## Validation Summary

- Every FR1 to FR18 is covered (see map). NFRs are verified in Epic 7 and enforced inside stories.
- Stories are ordered so none depends on a later story in its epic; tables are created by the story that needs them.
- No starter template is mandated by the architecture; Story 1.1 scaffolds the web app, Story 3.1 is the first AI story.
- Open: no UX contract yet; Practice, summary and generation stories each consume allowance; Check Understanding mode is deferred.
