# Push plan: spreading commits over 3 weeks

Last updated: 2026-11-06 (after Story 3.2; 50 commits queued, none pushed; calendar re-based from today).

## How this works (read once)

- GitHub's contribution graph uses the date a commit was **created**, not the date it was pushed. Pushing old commits later would still show the old date.
- So finished work is kept as local commits on the branch **`push-queue`** (never pushed). Each day you run one command that **replays** the next few queued commits onto `main` and pushes. Replayed commits are created at that moment (`git commit --reset-author`), so each carries the real date you ran the script. No dates are faked or edited.
- The work itself is real and already done and tested; only the publish day is spread out.
- `main` and GitHub stay at the last pushed commit until you run the script.

### Daily command

```
cd C:\Users\Windows11\Desktop\Solvely.ai
bash scripts/push-day.sh 3          # replay and push the next 3 queued commits
DRY_RUN=1 bash scripts/push-day.sh 3   # preview: replay locally, do NOT push
```

- Use the number from today's row in the calendar below (change it if you like).
- First run creates a sibling folder `..\Solvely.ai-pushwt` (a git worktree on `main`); your dev folder and uncommitted work are never touched.
- Needs `user.name`/`user.email` set in this repo (already set to AbdullahAnwar26 / abdullahanwar264@gmail.com) and GitHub credentials (already working).
- If it reports a conflict it stops at the last good commit; tell Claude.
- Do not commit by hand on `main`, and do not push `push-queue` itself.

### Rules Claude follows

1. After each finished and verified major part (a story or a coherent slice), Claude commits it on `push-queue` as small logical commits and does NOT push.
2. Claude then updates this file: adds the commits to the **Queue** table and assigns them to the earliest calendar days with room (target 2 to 6 per day, never 0, never more than 8).
3. Claude pushes to GitHub only when the user asks (for example, to run today's `push-day.sh`).

## Already on GitHub (cannot be changed)

| Date | Commits |
|---|---|
| Wed 2026-10-28 | 24 |
| Thu 2026-10-29 | 21 |

Total pushed: 45 (head `efc860b`, Epic 1 complete).

## Queue (committed locally on `push-queue`, not yet on GitHub)

The SHA is for reference only; replay order is the order below. Rebuilt from git on 2026-11-06.

| # | SHA | Commit | Part | Day |
|---|---|---|---|---|
| 1 | 96e7890 | feat(api): add Lesson model with create, retrieve and list endpoints | Story 2.1 | Fri Nov 6 |
| 2 | 56004c2 | test(api): let the isolation harness declare per-endpoint actions and UUID ids | Story 2.1 | Fri Nov 6 |
| 3 | 41e595b | test(api): cover lesson creation, retrieval, listing and cross-user access | Story 2.1 | Fri Nov 6 |
| 4 | 37a11d1 | feat(shared): regenerate API types with the lessons endpoints | Story 2.1 | Fri Nov 6 |
| 5 | e459fad | chore(web): add Excalidraw 0.18.1 and pin React 19 through overrides | Story 2.1 | Fri Nov 6 |
| 6 | a13f695 | feat(web): add lesson page with a lazily loaded Excalidraw board | Story 2.1 | Sat Nov 7 |
| 7 | ca58dd1 | feat(web): add New lesson action to the shell and the lesson route | Story 2.1 | Sat Nov 7 |
| 8 | c067bf2 | test(web): cover lesson creation, loading, not-found and board cleanup | Story 2.1 | Sat Nov 7 |
| 9 | 00fa4a2 | docs: close story 2.1 and record Excalidraw and React 19 notes | Story 2.1 | Sun Nov 8 |
| 10 | 524d75a | chore: add the push-day replay script and a 3-week push plan | tooling | Sun Nov 8 |
| 11 | 56e9b5f | chore: keep shell scripts on LF line endings | tooling | Sun Nov 8 |
| 12 | 523304b | feat(web): tag learner-created board elements with their origin | Story 2.2 | Mon Nov 9 |
| 13 | 528e7c9 | feat(web): add accessible zoom and fit controls for the board | Story 2.2 | Mon Nov 9 |
| 14 | c9e7f9d | feat(web): self-host Excalidraw fonts so drawing text makes no third-party requests | Story 2.2 | Mon Nov 9 |
| 15 | 7a9a1d2 | feat(web): wire origin tagging, controls and asset path into the lazy board | Story 2.2 | Mon Nov 9 |
| 16 | 9001eb4 | test(web): cover board controls, tagging and the stable Excalidraw mock | Story 2.2 | Mon Nov 9 |
| 17 | 30b8751 | docs: close story 2.2 and log font licence and production-build follow-ups | Story 2.2 | Tue Nov 10 |
| 18 | 0bf1923 | docs: update the push plan with the story 2.2 commits | tooling | Tue Nov 10 |
| 19 | b706582 | feat(api): add append-only BoardRevision model and strict board payload validation | Story 2.3 | Tue Nov 10 |
| 20 | a9e6954 | feat(api): save and load boards with optimistic concurrency, idempotent retries and pruning | Story 2.3 | Tue Nov 10 |
| 21 | f878fcb | test(api): extend the isolation harness to endpoints nested under a parent | Story 2.3 | Tue Nov 10 |
| 22 | 07136d3 | test(api): cover revisions, conflicts, idempotency, validation and concurrent saves | Story 2.3 | Wed Nov 11 |
| 23 | 912095c | feat(shared): regenerate API types with the board endpoints | Story 2.3 | Wed Nov 11 |
| 24 | 2787082 | feat(web): add board serialization with a change fingerprint and the board API client | Story 2.3 | Wed Nov 11 |
| 25 | 4ac729e | feat(web): add the autosave state machine with debounce, backoff and conflict handling | Story 2.3 | Wed Nov 11 |
| 26 | e86d569 | feat(web): show save status, handle conflicts and load the latest revision on open | Story 2.3 | Wed Nov 11 |
| 27 | 73c616a | test(web): cover serialization, the autosave state machine and the page-level save flow | Story 2.3 | Thu Nov 12 |
| 28 | fe3590d | docs: close story 2.3 and log autosave polish and recovery follow-ups | Story 2.3 | Thu Nov 12 |
| 29 | e2922ce | docs: update the push plan with the story 2.3 commits | tooling | Thu Nov 12 |
| 30 | 789e628 | feat(web): add validated device-local draft storage with a throttled writer | Story 2.4 | Thu Nov 12 |
| 31 | 03b5f16 | feat(web): add cheap dirty detection, the unsaved state and a safe viewport fallback | Story 2.4 | Thu Nov 12 |
| 32 | 39645c1 | feat(web): offer draft recovery and restore the saved viewport on open | Story 2.4 | Fri Nov 13 |
| 33 | 6c4f275 | feat(web): remove local drafts on sign-out and account deletion | Story 2.4 | Fri Nov 13 |
| 34 | 8d084d3 | test(web): cover draft recovery, storage rules and the unsaved flow | Story 2.4 | Fri Nov 13 |
| 35 | 2347794 | docs: close story 2.4 and mark epic 2 complete | Story 2.4 | Fri Nov 13 |
| 36 | 33593b4 | docs: update the push plan with the story 2.4 commits | tooling | Fri Nov 13 |
| 37 | 3895ece | feat(api): add the AI provider port, typed errors and strict JSON parsing | Story 3.1 | Sat Nov 14 |
| 38 | 2af70a8 | feat(api): add AIService with bounded retries, an overall deadline and a concurrency cap | Story 3.1 | Sat Nov 14 |
| 39 | d971a06 | feat(api): add a deterministic FakeProvider with fixtures and failure injection | Story 3.1 | Sat Nov 14 |
| 40 | 7beba9f | feat(api): add the Gemini adapter as the only google-genai importer | Story 3.1 | Sun Nov 15 |
| 41 | 7ea0b95 | feat(api): add the admin-only AI status endpoint and AI settings | Story 3.1 | Sun Nov 15 |
| 42 | 7cb1545 | feat(shared): regenerate API types with the AI status endpoint | Story 3.1 | Sun Nov 15 |
| 43 | 3cb78cb | test(api): cover the AI service, Gemini adapter, import guards and diagnostics offline | Story 3.1 | Mon Nov 16 |
| 44 | 77b2298 | docs: close story 3.1 and log the live-check follow-up | Story 3.1 | Mon Nov 16 |
| 45 | 3fe1152 | test(api): give the live Gemini smoke test realistic timeouts and record verified models | Story 3.1 follow-up | Mon Nov 16 |
| 46 | 145e91e | feat(api): add the versioned LessonStep schema with strict unknown-field rejection | Story 3.2 | Mon Nov 16 |
| 47 | dc3bf69 | feat(api): add the atomic Board Operation validator with server-allocated element ids | Story 3.2 | Mon Nov 16 |
| 48 | 5d32df1 | feat(api): carry a UUID-validated Step id through the provider request | Story 3.2 | Tue Nov 17 |
| 49 | 167649e | test(api): cover the lesson schema, validator, viewport operations and Step id validation | Story 3.2 | Tue Nov 17 |
| 50 | 6f1d49e | docs: close story 3.2 after independent review and log the viewport defect | Story 3.2 | Tue Nov 17 |
| 51 | (queued) | docs: refresh the push plan with the catch-up schedule | tooling | Tue Nov 17 |

## Calendar (re-based on 2026-11-06 with the catch-up rule)

The original calendar (Fri Oct 30 to Thu Nov 5, 23 commits) was not run: no pushes happened on those 7 days, so they stay empty on the contribution graph and cannot be recovered. Catch-up: 5 commits on weekdays and 3 on weekends (never more than 6 a day). "Planned" means commits that already exist in the queue; "Forecast" means commits that will exist once that part is built and verified.

| Date | Day | Target | Status | Content |
|---|---|---|---|---|
| 2026-11-06 | Fri | 5 | Planned | Queue #1 to #5: Story 2.1 |
| 2026-11-07 | Sat | 3 | Planned | Queue #6 to #8: Story 2.1 |
| 2026-11-08 | Sun | 3 | Planned | Queue #9 to #11: Story 2.1, tooling |
| 2026-11-09 | Mon | 5 | Planned | Queue #12 to #16: Story 2.2 |
| 2026-11-10 | Tue | 5 | Planned | Queue #17 to #21: Story 2.2, tooling, Story 2.3 |
| 2026-11-11 | Wed | 5 | Planned | Queue #22 to #26: Story 2.3 |
| 2026-11-12 | Thu | 5 | Planned | Queue #27 to #31: Story 2.3, tooling, Story 2.4 |
| 2026-11-13 | Fri | 5 | Planned | Queue #32 to #36: Story 2.4, tooling |
| 2026-11-14 | Sat | 3 | Planned | Queue #37 to #39: Story 3.1 |
| 2026-11-15 | Sun | 3 | Planned | Queue #40 to #42: Story 3.1 |
| 2026-11-16 | Mon | 5 | Planned | Queue #43 to #47: Story 3.1, Story 3.1 follow-up, Story 3.2 |
| 2026-11-17 | Tue | 5 | Planned + Forecast | Queue #48 to #51: Story 3.2, tooling; plus 1 from Story 3.3 deterministic layout engine |
| 2026-11-18 | Wed | 5 | Forecast | Story 3.3 tests and docs; Story 3.4 daily Lesson Allowance |
| 2026-11-19 | Thu | 5 | Forecast | Story 3.4 tests; Story 3.5 Explain and Solve generation |
| 2026-11-20 | Fri | 5 | Forecast | Story 3.5 tests and docs |
| 2026-11-21 | Sat | 3 | Forecast | Story 3.6 step player on the board |
| 2026-11-22 | Sun | 3 | Forecast | Story 3.6 tests; Epic 3 close-out docs |
| 2026-11-23 | Mon | 5 | Forecast | Epic 4 start: follow-up questions on the current Step |
| 2026-11-24 | Tue | 5 | Forecast | Hint and Simplify modes |
| 2026-11-25 | Wed | 5 | Forecast | Cancel, retry and recover generations |
| 2026-11-26 | Thu | 5 | Forecast | To be assigned as work completes |

Capacity note: new finished work is appended to the queue and assigned to the earliest day with room (target 2 to 6 a day, never 0). If work finishes slower than the calendar, forecast rows without commits are merged and days are re-balanced so none is empty.

## Catch-up rule

If a day is missed, do not dump the backlog: replay at most 6 the next day and carry the rest forward.
