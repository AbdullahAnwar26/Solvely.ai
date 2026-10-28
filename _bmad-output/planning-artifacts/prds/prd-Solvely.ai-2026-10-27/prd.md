---
title: Whiteboard Tutor
status: final
created: 2026-10-27
updated: 2026-10-27
---

# PRD: Whiteboard Tutor
*Working title; the product name is an open question.*

## 0. Document Purpose
This PRD defines v1 of a free, whiteboard-first AI tutor for the product owner, stakeholders, and the downstream UX, architecture and epic workflows. Vocabulary is anchored in the Glossary (§3). Features (§4) group numbered FRs; inferences are tagged `[ASSUMPTION]` inline and indexed in §9. It builds on `briefs/brief-Solvely.ai-2026-10-27/brief.md` and its addendum, and does not repeat their research. Technology choices live in the addendum and architecture, not here.

## 1. Vision
Whiteboard Tutor teaches the way a good teacher does: it works through a problem step by step on a **Board** it draws as it explains, and the learner can edit that Board, pause, ask "simpler?" or "why?", and practise afterwards. The Board is the product, not a chat window with diagrams attached.

It is free. Learners get a daily **Lesson Allowance** instead of a trial clock or paywall, so a student who can't afford a subscription can still learn. v1 serves adults 18+: college students and IT/programming learners. High school is a later phase (see §2.2).

## 2. Target User

### 2.1 Jobs To Be Done
- When I'm stuck on a homework or coding problem, I want it taught step by step so I understand the method, not just the answer.
- When I'm short of money, I want a tutor that doesn't lock me out after a few minutes.
- When I revise, I want to reopen a past Lesson and see its Board exactly as it was.
- When I don't follow a step, I want a simpler re-explanation of that step only.
- When I think I've understood, I want to check myself with practice questions.

### 2.2 Non-Users (v1)
- Under-18s. Gemini's API terms (verified 2026-10-27) bar apps directed at or likely accessed by under-18s. Revisit with a provider or consent flow that permits minors.
- Classrooms/teachers, institutions, anyone needing image/PDF input.

### 2.3 Key User Journeys
- **UJ-1. Maya, second-year CS student, learns Big-O from a sorting snippet.**
  - **Persona + context:** Maya, 20, has an exam Friday and can't explain why her nested loop is O(n²).
  - **Entry state:** signed in on a laptop, empty workspace.
  - **Path:** starts a new Lesson, pastes her code, picks Explain; the Board fills step by step: code block, loop annotations, a growth diagram; she pauses at step 3, asks "why n² and not 2n?"
  - **Climax:** the answer redraws step 3 with a worked count of iterations; she sees it.
  - **Resolution:** Lesson saved; she resumes tomorrow from step 3.
  - **Edge case:** the AI returns a malformed step; the Board is untouched, an error shows, Maya retries.
- **UJ-2. Dev, first-year engineering student, solves a calculus problem and gets stuck.**
  - **Persona + context:** Dev, 19, typing a derivative problem at midnight.
  - **Entry state:** signed in, mobile phone.
  - **Path:** enters the problem, picks Solve; reads step 1, requests a Hint instead of the next step; uses Simplify on step 2.
  - **Climax:** after two hints he completes the step himself.
  - **Resolution:** progress shows steps he completed himself.
  - **Edge case:** he exhausts his Lesson Allowance mid-Lesson; the current Lesson can be finished, new ones wait until reset.
- **UJ-3. Priya, bootcamp learner, edits the Board and practises.**
  - **Persona + context:** Priya, 27, learning SQL joins evenings.
  - **Entry state:** signed in, tablet.
  - **Path:** reopens a saved Lesson, draws her own arrows on the Board, adds a note, asks for practice questions.
  - **Climax:** an AI update redraws one step and her arrows survive.
  - **Resolution:** she answers 3 questions; the Lesson records them.

## 3. Glossary
- **Lesson** — a saved teaching session owned by one Learner: a title, Teaching Mode, ordered Steps, Board history, and conversation.
- **Learner** — a signed-in adult user (18+ confirmed).
- **Board** — the editable whiteboard of a Lesson, containing AI Content and Learner Content.
- **AI Content / Learner Content** — Board elements created by the tutor versus by the Learner; AI updates never delete Learner Content.
- **Step** — one unit of teaching: a Board change plus its explanation.
- **Teaching Mode** — Explain, Solve, Hint, Simplify, Practice, Check Understanding.
- **Board Operation** — one validated, vocabulary-limited change to the Board (add, update, remove, highlight, set viewport).
- **Lesson Allowance** — free generations per Learner per day; resets daily.
- **Board Revision** — a numbered saved version of a Board.

## 4. Features

### 4.1 Learning Workspace
**Description:** The main screen: Board centre, explanation panel beside it (below on narrow screens), request input, Step controls. Realizes UJ-1, UJ-2, UJ-3.

#### FR-1: Interactive Board
A Learner can draw shapes, arrows, text and freehand, select, move, resize and delete elements, zoom, pan, fit to content, undo and redo.
**Consequences (testable):**
- Edits to any element persist after reload.
- Learner Content is visually distinguishable from AI Content.

#### FR-2: Teaching request
A Learner can submit a question or problem with a chosen Teaching Mode and receive a Lesson with Steps.
**Consequences (testable):**
- Request over the configured length limit is rejected with a clear message.
- A request while the Allowance is exhausted is refused with the reset time.

#### FR-3: Step-by-step delivery
A Learner can play, pause, resume, restart, and jump between Steps; each Step shows its explanation and Board change.
**Consequences (testable):**
- Jumping to a Step shows that Step's Board state.
- Controls are reachable by keyboard.

#### FR-4: Follow-up questions
A Learner can ask a follow-up tied to the current Step; the answer may add or modify AI Content.
**Consequences (testable):**
- Follow-ups do not regenerate the whole Lesson.
- Learner Content survives every AI update.

#### FR-5: Mathematics and code rendering
Equations render as typeset math; code is shown in copyable monospace blocks.
**Consequences (testable):**
- A Learner can copy an equation's source and a code block.
- Where a result is computed deterministically (arithmetic, code output), the UI marks it as verified; otherwise it is unmarked. `[ASSUMPTION: verified-computation covers arithmetic/algebra only in v1.]`

### 4.2 Teaching Engine
**Description:** Backend turns a request into a teaching plan, Steps and Board Operations. Output is validated before use.

#### FR-6: Validated AI output
The system accepts AI output only if it matches the versioned lesson schema and Board Operation limits.
**Consequences (testable):**
- Malformed, oversized or out-of-vocabulary output is rejected, and the existing Board is unchanged.
- Bounded retries (max configured) before a visible, retryable error. No fabricated fallback explanation is ever shown.

#### FR-7: Teaching Modes
Explain, Solve, Hint, Simplify work end to end in v1; Practice and Check Understanding follow in the same release only if the core is reliable (see §6).
**Consequences (testable):**
- Hint reveals progressively without giving the final answer first.
- Simplify rewrites only the current Step.

#### FR-8: Readable layout
Generated content lays out without overlap or clipping for sequential solutions, flowcharts, concept maps, code walkthroughs.
**Consequences (testable):**
- Fixture suite (long text, large diagrams, repeated operations) produces no overlapping elements.

#### FR-9: Cancel and recover
A Learner can cancel a running generation; an interrupted or failed generation leaves the prior Lesson and Board intact.

### 4.3 Lessons and Continuity

#### FR-10: Save and resume
Lessons autosave; a Learner can close the browser and resume at the same Step with the same Board and history.
**Consequences (testable):**
- A stale save never overwrites a newer Board Revision (409 on conflict).
- Visible save status (saved / saving / failed).

#### FR-11: Lesson library
A Learner can list, search, filter, rename, duplicate, archive and delete Lessons.
**Consequences (testable):**
- Delete is permanent after confirmation; deleted Lessons return not-found.

#### FR-12: Export
A Learner can export a Board image and a Lesson file.

### 4.4 Practice and Notes

#### FR-13: Practice questions
A Learner can request practice questions linked to a Lesson's concepts, answer them, and see an explanation.
**Consequences (testable):** Attempts are stored with the Lesson.

#### FR-14: Notes and summaries
A Learner can add personal notes to a Step and get a Lesson summary with key takeaways.

### 4.5 Accounts, Access and Allowance

#### FR-15: Accounts and age gate
A person registers with email and password and must confirm they are 18+. Sessions are secure; password reset works by email.
**Consequences (testable):**
- Registration without the 18+ confirmation is rejected.
- No social-login control is shown unless configured.

#### FR-16: Isolation
A Learner can only read or change their own Lessons, Board Revisions, notes and usage.
**Consequences (testable):**
- Another Learner's Lesson ID returns not-found, never data.

#### FR-17: Free daily allowance
Each Learner gets a daily Lesson Allowance, shown in the UI; there is a global ceiling protecting the operator's spend.
**Consequences (testable):**
- Remaining allowance and reset time are visible.
- When the global ceiling is hit, the Learner sees an honest "at capacity" message. `[ASSUMPTION: starting allowance 5 Lessons/day; tune after measuring real cost.]`

#### FR-18: Account deletion and privacy
A Learner can delete their account and all data; a privacy notice states what is sent to the AI provider.

## 5. Non-Goals (Explicit)
- Not a general chatbot, not a homework-answer generator without teaching.
- Not for under-18s in v1; no age-evasion workarounds.
- No payment, ads, or paywall in v1.
- No claim of capabilities not shipped (OCR, file understanding, collaboration).
- Not a replacement for human teachers or an accredited course.

## 6. MVP Scope

### 6.1 In Scope
FR-1 to FR-18. Explain, Solve, Hint, Simplify; Practice (FR-13) included; Check Understanding `[NON-GOAL for MVP]` unless time remains.

### 6.2 Out of Scope for MVP
- Image/PDF/OCR input; real-time collaboration; teacher/classroom tools; billing; native mobile apps; high-school audience (blocked by provider terms).

## 7. Success Metrics (first 90 days after public launch; all `[ASSUMPTION]`)

**Primary**
- **SM-1**: Activation — 60% of new Learners reach the last Step of a first Lesson. Validates FR-2, FR-3.
- **SM-2**: 7-day return — 25% of Learners return within 7 days. Validates FR-10, FR-11.
- **SM-3**: Depth — median 3 Lessons per active Learner per week. Validates FR-2, FR-13.

**Secondary**
- **SM-4**: 80% thumbs-up on rated Lessons; <2% of generations end in a visible error. Validates FR-6, FR-8, FR-9.
- **SM-5**: 1,000 registered Learners. Validates FR-15.

**Counter-metrics (do not optimize)**
- **SM-C1**: Time-on-site — not a goal; learners should finish and leave. Counterbalances SM-2/SM-3.
- **SM-C2**: Cost per Lesson — must stay within the operator budget even if usage grows. Counterbalances SM-3.
- **SM-C3**: Answers revealed before attempts (Hint bypass) — high values mean we're not teaching. Counterbalances SM-1.

## 8. Cross-Cutting Requirements

### 8.1 NFRs
- **Performance:** first Step visible within 10 s at p90 under normal load `[ASSUMPTION; validate]`; Board interaction stays smooth on an 8 GB laptop for Boards up to ~500 elements `[ASSUMPTION]`.
- **Security:** object-level authorization everywhere; rate limits on AI and auth endpoints; secrets never reach the browser; AI output, user input and uploaded text treated as untrusted (prompt-injection defences); no stack traces in responses.
- **Accessibility:** keyboard navigation, visible focus, reduced-motion respect, WCAG 2.2 AA target for core flows; light/dark themes.
- **Reliability:** explicit timeouts and bounded retries on AI calls; health and readiness endpoints; recoverable save failures.
- **Responsive:** laptop, tablet and mobile layouts reorganise, not just shrink.

### 8.2 Constraints and Guardrails
- **Safety:** content-safety handling for AI output; the tutor refuses requests to bypass system rules.
- **Privacy:** no full prompts or student content in logs by default; clear deletion path; AI provider processing disclosed.
- **Cost:** paid-tier AI provider; per-Learner and global usage limits; usage accounting per request.
- **Legal:** 18+ gate at sign-up; legal review of terms/privacy before public launch `[NOTE FOR PM]`.
- **Provider portability:** teaching logic is independent of the AI provider so another provider can be added later (needed for the high-school phase).

## 9. Open Questions
1. Product name and identity.
2. Real daily Lesson Allowance and who funds the AI bill past early usage.
3. Launch channel and first 50 target users for validation interviews.
4. Does Solvely (or any competitor) actually teach on a drawn whiteboard? Verify before pitching differentiation.
5. Which provider could serve minors in a later phase, and what consent flow it needs.
6. Legal review of age gate, privacy notice and data-processing terms.

## 10. Assumptions Index
- §4.1 FR-5 — verified computation limited to arithmetic/algebra in v1.
- §4.5 FR-17 — starting allowance of 5 Lessons/day.
- §7 SM-1 to SM-5 — all targets are proposed, not validated.
- §8.1 — p90 10 s first Step; ~500 element Board on an 8 GB laptop.
- §2.3 — journey personas and details are illustrative, not from user interviews.
