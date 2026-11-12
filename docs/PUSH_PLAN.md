# Push plan: spreading commits over 3 weeks

Last updated: 2026-10-29 (after Story 2.2; 18 commits queued, none pushed). Planning window: Fri 2026-10-30 to Thu 2026-11-19 (21 days).

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

The SHA is for reference only; replay order is the order below.

| # | SHA | Commit | Part | Day |
|---|---|---|---|---|
| 1 | 96e7890 | feat(api): add Lesson model with create, retrieve and list endpoints | Story 2.1 | Fri Oct 30 |
| 2 | 56004c2 | test(api): let the isolation harness declare per-endpoint actions and UUID ids | Story 2.1 | Fri Oct 30 |
| 3 | 41e595b | test(api): cover lesson creation, retrieval, listing and cross-user access | Story 2.1 | Fri Oct 30 |
| 4 | 37a11d1 | feat(shared): regenerate API types with the lessons endpoints | Story 2.1 | Sat Oct 31 |
| 5 | e459fad | chore(web): add Excalidraw 0.18.1 and pin React 19 through overrides | Story 2.1 | Sat Oct 31 |
| 6 | a13f695 | feat(web): add lesson page with a lazily loaded Excalidraw board | Story 2.1 | Sun Nov 1 |
| 7 | ca58dd1 | feat(web): add New lesson action to the shell and the lesson route | Story 2.1 | Sun Nov 1 |
| 8 | c067bf2 | test(web): cover lesson creation, loading, not-found and board cleanup | Story 2.1 | Mon Nov 2 |
| 9 | 00fa4a2 | docs: close story 2.1 and record Excalidraw and React 19 notes | Story 2.1 | Mon Nov 2 |
| 10 | (queued) | chore: add the push-day replay script and a 3-week push plan | tooling | Mon Nov 2 |
| 11 | (queued) | chore: keep shell scripts on LF line endings | tooling | Mon Nov 2 |
| 12 | 523304b | feat(web): tag learner-created board elements with their origin | Story 2.2 | Tue Nov 3 |
| 13 | 528e7c9 | feat(web): add accessible zoom and fit controls for the board | Story 2.2 | Tue Nov 3 |
| 14 | c9e7f9d | feat(web): self-host Excalidraw fonts so drawing text makes no third-party requests | Story 2.2 | Tue Nov 3 |
| 15 | 7a9a1d2 | feat(web): wire origin tagging, controls and asset path into the lazy board | Story 2.2 | Tue Nov 3 |
| 16 | 9001eb4 | test(web): cover board controls, tagging and the stable Excalidraw mock | Story 2.2 | Wed Nov 4 |
| 17 | 30b8751 | docs: close story 2.2 and log font licence and production-build follow-ups | Story 2.2 | Wed Nov 4 |
| 18 | (queued) | docs: update the push plan with the story 2.2 commits | tooling | Wed Nov 4 |

## Calendar

"Planned" means commits that already exist in the queue. "Forecast" means commits that will exist once that part is built and verified; the numbers move as work completes, and Claude updates this table.

| Date | Day | Target | Status | Content |
|---|---|---|---|---|
| 2026-10-30 | Fri | 3 | Planned | Queue #1 to #3: Lesson API, isolation harness, lesson tests |
| 2026-10-31 | Sat | 2 | Planned | Queue #4 to #5: shared API types, Excalidraw dependency |
| 2026-11-01 | Sun | 2 | Planned | Queue #6 to #7: lesson page with Board, New lesson action |
| 2026-11-02 | Mon | 4 | Planned | Queue #8 to #11: web tests, Story 2.1 docs, push tooling |
| 2026-11-03 | Tue | 4 | Planned | Queue #12 to #15: Story 2.2 origin tagging, zoom and fit controls, self-hosted fonts, board wiring |
| 2026-11-04 | Wed | 4 | Planned + Forecast | Queue #16 to #18: Story 2.2 tests, docs, plan update; plus 1 from Story 2.3 backend (BoardRevision, optimistic concurrency) |
| 2026-11-05 | Thu | 4 | Forecast | Story 2.3 tests; autosave in the web app |
| 2026-11-06 | Fri | 4 | Forecast | Story 2.3 web tests; Story 2.4 resume and recovery |
| 2026-11-07 | Sat | 2 | Forecast | Story 2.4 tests; Epic 2 close-out docs |
| 2026-11-08 | Sun | 2 | Forecast | Epic 3 start: AI provider port, FakeProvider, Gemini adapter |
| 2026-11-09 | Mon | 4 | Forecast | Story 3.1 tests; Story 3.2 lesson schema and Board Operation validator |
| 2026-11-10 | Tue | 4 | Forecast | Story 3.2 tests; Story 3.3 deterministic layout engine |
| 2026-11-11 | Wed | 4 | Forecast | Story 3.3 tests; Story 3.4 daily Lesson Allowance |
| 2026-11-12 | Thu | 4 | Forecast | Story 3.4 tests; Story 3.5 Explain and Solve generation |
| 2026-11-13 | Fri | 4 | Forecast | Story 3.5 tests; Story 3.6 step player |
| 2026-11-14 | Sat | 2 | Forecast | Story 3.6 tests; Epic 3 close-out docs |
| 2026-11-15 | Sun | 2 | Forecast | Epic 4 start: follow-ups on the current Step |
| 2026-11-16 | Mon | 4 | Forecast | Hint and Simplify modes |
| 2026-11-17 | Tue | 4 | Forecast | Cancel, retry and recover generations |
| 2026-11-18 | Wed | 4 | Forecast | Math and code rendering with verified marks |
| 2026-11-19 | Thu | 4 | Forecast | Keyboard shortcuts dialog; Epic 4 close-out docs |

Capacity note: Epics 5 to 7 (practice, library and export, launch readiness) are not in this window. If work finishes faster than the calendar, the queue simply grows and later days can take up to 8 commits; if it finishes slower, forecast rows without commits are skipped or merged and days are re-balanced so none is empty.

## Catch-up rule

If a day is missed, do not dump the backlog: replay at most 6 the next day and carry the rest forward.
