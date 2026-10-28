---
title: Solvely.ai Product Brief
status: complete
created: 2026-10-27
updated: 2026-10-27
---

# Product Brief: Whiteboard Tutor (working title; original identity, inspired by Solvely.ai)

## The idea
A free AI tutor that teaches the way a good teacher does: it works through a problem step by step **on a whiteboard it draws as it explains**, and the student can edit that board, interrupt, and ask "simpler?" or "why?". The board is the product, not a chat window with diagrams attached.

## Who it is for
- **v1 (launch):** adult learners (18+): **college students** and **IT/programming learners**.
- **Later:** high-school students. Deferred, not dropped: Google's Gemini API terms (verified 2026-10-27) require users to be 18+ and bar apps directed at or likely used by under-18s. High school needs a minors-permitted provider or consent flow first. See addendum.

## The problem
Students get answers from chatbots but not *teaching*: no visual derivation, no way to manipulate the explanation, and tools that do teach step by step (e.g. Solvely) paywall after a short trial. [ASSUMPTION: the pain is "I can't afford to keep learning", not only "I want better explanations". Needs validation with 5-10 target users.]

## What makes it different
1. **Teaching on a live, editable whiteboard** (Excalidraw), with steps the student can pause, replay, and annotate.
2. **Free to use**, with a daily lesson allowance instead of a time-limited trial or paywall.
3. **Honest correctness:** arithmetic and code results are computed deterministically where possible, not trusted from the model.
4. Original design and architecture. No Solvely code, branding or assets.

[UNVERIFIED: whether Solvely or others already offer a true drawn-whiteboard experience. Our research did not confirm one. Verify before pitching "nobody does this".]

## v1 scope
Explain, Solve, Hint, Simplify and follow-up modes; persistent lessons (save, resume, search); schema-validated AI output turned into safe board operations; accounts with per-user data isolation; daily usage caps. Practice and check-understanding modes follow once the core is reliable.

**Not in v1:** image/PDF/OCR input, real-time collaboration, classrooms, billing.

## Success measures (first 90 days after public launch)
All [ASSUMPTION], to be confirmed or replaced by you:
- Activation: **60%** of new users complete a first lesson (reach the last step).
- Retention: **25%** of users return within 7 days.
- Depth: median **3 lessons per active user per week**.
- Quality: **80%** of rated lessons get a thumbs-up; **<2%** of generations fail with a visible error.
- Reach: **1,000 registered users** within 90 days [ASSUMPTION; depends on launch channel].

## Constraints and risks
- **Cost of "free":** Gemini free tier has shared per-project quota, is unusable for EU/UK/CH users, and Google may train on its content. We use paid-tier Gemini with a per-user daily cap, so the operator carries the bill. [UNVERIFIED: real monthly cost. Needs a lessons/day x tokens/lesson estimate.]
- **Age gate:** 18+ confirmation at sign-up is mandatory for v1, with no student content logged by default.
- **AI quality:** model can be wrong or return malformed output; mitigated by schema validation, deterministic checks and no fake fallbacks.
- **Provider lock-in:** teaching logic sits behind a provider interface so a minors-permitted provider can be added.
- **Solo build, 8 GB dev machine:** modular monolith, no local LLMs.

## Open questions
1. Who funds the Gemini bill past the first few hundred users (self, sponsor, donations)?
2. Daily cap: how many lessons per user per day?
3. Launch channel (campus groups, r/learnprogramming, Product Hunt)?
4. Product name and identity.
5. Legal review of age gate and data handling before launch.
