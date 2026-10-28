---
title: Whiteboard Tutor — Experience Spine
name: Whiteboard Tutor
status: final
created: 2026-10-28
updated: 2026-10-29
sources:
  - _bmad-output/planning-artifacts/prds/prd-Solvely.ai-2026-10-27/prd.md
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/architecture/architecture-Solvely.ai-2026-10-27/ARCHITECTURE-SPINE.md
companion: DESIGN.md
---

# Whiteboard Tutor — Experience Spine

## Foundation

Single-surface **responsive web SPA**: React 19 + TypeScript + Vite in `apps/web`, served same-origin with the Django API (AD-6). The Board is **Excalidraw 0.18** wrapped by one typed board adapter (AD-2); AI changes reach it only as validated Board Operations. Styling is **CSS custom properties generated from `DESIGN.md` tokens** (`--color-*`, `--space-*`, `--radius-*`, `--font-*`), swapped by `[data-theme]`, on top of **headless accessible primitives** (Radix UI or equivalent `[ASSUMPTION]`, confirm at Story 1.1) for dialog, menu, tabs, tooltip, toast, toggle group and sheet. `DESIGN.md` is the visual contract; this file is the behavioural contract. Spine wins over any mockup.

Product posture: a calm study room where the Board is the star. The learner should always know (1) which Step they are on, (2) what the tutor drew versus what they drew, (3) whether their work is saved, and (4) how many lessons they have left today.

## Information Architecture

| Surface | Route `[ASSUMPTION]` | Reached from | Purpose | FRs |
|---|---|---|---|---|
| Sign up | `/signup` | Landing, sign-in link | Email, password, **18+ confirmation**, privacy notice link | FR-15, FR-18 |
| Sign in | `/signin` | Landing, session expiry | Email + password | FR-15 |
| Password reset (request / set new) | `/reset`, `/reset/:token` | Sign-in "Forgot password?" | Email link reset | FR-15 |
| App shell | all `/app/*` | After sign-in | Collapsible sidebar: **New lesson**, Library, Settings; Allowance indicator in footer | FR-17 |
| New lesson (composer state of workspace) | `/app/new` | Sidebar "New lesson", `N` | Empty Board + request composer + mode selector | FR-2 |
| Learning workspace | `/app/lessons/:id` | Library, New lesson, resume | Board + explanation panel (tabs Steps · Notes · Practice · Summary) + step bar + follow-up composer | FR-1–FR-5, FR-9, FR-10, FR-13, FR-14 |
| Lesson library | `/app/lessons` | Sidebar, `G L` | List, search, filter (mode, archived), rename, duplicate, archive, delete | FR-11 |
| Practice (workspace tab) | `/app/lessons/:id?tab=practice` | Panel tab, mode "Practice" | Questions, answer, explanation, stored attempts | FR-13 |
| Notes & Summary (workspace tabs) | `?tab=notes`, `?tab=summary` | Panel tabs | Per-Step notes; Lesson summary + key takeaways | FR-14 |
| Export (dialog) | workspace overflow menu, library card menu | `Ctrl/⌘+Shift+E` | Board image (PNG/SVG) and Lesson file (JSON) | FR-12 |
| Account settings | `/app/settings` | Sidebar, avatar menu | Email, password change, theme (System/Light/Dark), reduce motion, sign out, **Delete account** | FR-15, FR-18 |
| Privacy notice | `/privacy` (public) | Sign-up, settings, footer | What is stored, what is sent to the AI provider (Google Gemini), deletion | FR-18 |
| Not found | any | Foreign or deleted Lesson id | "We couldn't find that lesson." — identical for foreign and deleted ids | FR-11, FR-16 |

**FR coverage:** FR-1 Board · FR-2 composer · FR-3 step bar · FR-4 follow-up composer · FR-5 panel renderers · FR-9 cancel/retry in composer + alerts · FR-10 save status · FR-11 library · FR-12 export dialog · FR-13 Practice tab · FR-14 Notes/Summary tabs · FR-15 auth surfaces · FR-16 not-found surface · FR-17 allowance indicator + exhausted/at-capacity states · FR-18 settings delete + privacy notice. FR-6/7/8 are engine requirements surfaced through states (generation failed) and the mode selector.

Navigation: sidebar on laptop (collapsible to icon rail, state remembered per device); icon rail + sheet on tablet; top bar + sheet on phone. Dialogs stack at most one level.

## Voice and Tone

Calm, encouraging, honest. Talk like a patient tutor sitting beside the learner. Short sentences. Never blame the learner. Never pretend: if the tutor failed, say so and offer retry; never show a made-up explanation (AD-11).

| Do | Don't |
|---|---|
| "What are you stuck on?" (composer placeholder) | "Ask me anything! 🚀" |
| "Drawing step 2 of 6…" | "Generating response…" |
| "That didn't come out right, so I left your Board as it was. Try again?" | "Oops! Something went wrong." / any fabricated fallback answer |
| "You've used today's 5 lessons. New ones unlock at 00:00 (in 3 h 12 min). You can keep working in this lesson." | "Limit reached. Upgrade for more!" |
| "We're at capacity right now. Your work is safe; please try again in a few minutes." | "Service unavailable (503)." |
| "Saved" · "Saving…" · "Couldn't save. Retry" | "Autosave error code 409" |
| "This board changed in another tab. Load the newer version?" | "Conflict detected." |
| "Nice — you worked that step out yourself." (once, after a learner-completed step) | Streaks, badges, "🎉 Amazing!!" |
| "Verified by calculation" | "100% correct!" on unverified AI claims |
| "Delete this lesson? This can't be undone." | "Are you sure?" |

Error copy always has: what happened (plain words), what is safe ("your Board is unchanged"), and the next action. Include a short reference (`request_id`) in a "Details" disclosure, never in the headline.

## Component Patterns

Behavioural rules. Visual specs live in `DESIGN.md` → Components.

| Component | Use | Behavioural rules |
|---|---|---|
| Request composer | New lesson; follow-up at bottom of panel | `Enter` submits, `Shift+Enter` newline. Mode selector is a radio group (arrow keys). Character counter live; over limit disables submit and shows the limit message (FR-2). While generating, submit becomes **Cancel** (`Esc` also cancels). Follow-ups are scoped to the current Step and labelled "Asking about step 3". |
| Mode selector | Composer | Explain · Solve · Hint · Simplify · Practice. Hint and Simplify act on the current Step and are disabled with a reason tooltip when there is no Step. Check Understanding hidden in v1. |
| Board (Excalidraw) | Workspace centre | Full Excalidraw editing (FR-1). New learner elements get `origin=learner` styling defaults (`{components.board-learner-element}`). AI elements are not locked, the learner may move them, but AI never edits learner elements (AD-3). "Show who drew what" toggle. Zoom-to-fit button and `Shift+1`. |
| Step bar | Workspace bottom | Restart · Previous · Play/Pause · Next; dot rail is a `tablist`-like list of buttons ("Step 3 of 7: Count the inner loop"). Jumping shows that Step's Board state (FR-3). Play auto-advances at reading pace (`[ASSUMPTION]` 1.2 s per 20 words, min 4 s) and pauses on any learner Board edit or panel scroll. |
| Explanation panel | Workspace right / sheet | Tabs Steps · Notes · Practice · Summary. Steps tab scrolls to and highlights the current Step; selecting a Step in the panel jumps the Board. Resizable on laptop; collapsible (`Ctrl/⌘+.`) to give the Board full width. |
| Code block / math | Panel and Board-linked text | Copy buttons copy raw source / LaTeX; announce "Copied". Verified mark only from server `verified=true` (AD-10). |
| Practice question card | Practice tab | One question at a time; answer field; "Check" reveals explanation; attempt stored (FR-13). "Show answer" requires a second confirmation ("Try once more first?") to protect learning (SM-C3). |
| Note editor | Notes tab | Plain text per Step, autosaves with the same status indicator; shows Step title it belongs to. |
| Allowance indicator | Sidebar footer / phone account menu | Shows remaining + reset time (FR-17). Updates after every charged generation and refund. Click opens a popover explaining the daily allowance. |
| Save status | Panel header | Debounced autosave (`[ASSUMPTION]` 1.5 s idle) + save on Step change. States: Saved / Saving… / Couldn't save · Retry. |
| Lesson card / row | Library | Click opens; overflow menu: Rename (inline), Duplicate, Archive/Unarchive, Export, Delete (confirm dialog). Search is debounced 250 ms; filters are chips (All · Archived · by mode). Pagination ("Load more" button), no infinite scroll. |
| Confirm dialog | Delete lesson, delete account, discard | Default focus on the safe action. Delete account requires typing the email and the password (FR-18). |
| Toast | Non-blocking confirmations | "Lesson duplicated", "Exported". Polite live region; auto-dismiss 5 s; never used for errors that need action (use inline alert). |

## State Patterns

| State | Surface | Treatment |
|---|---|---|
| Cold load | Shell, library, workspace | Skeletons matching layout; Board shows `board` background immediately; panel skeleton lines. No spinner over the Board. |
| Generating (first Step) | Workspace | Composer shows "Cancel"; panel shows "Planning your lesson…" then "Drawing step 1 of N…" with calm pulse (static under reduced motion). Board stays interactive; AI elements arrive per Step. |
| Empty — new lesson | Workspace | Board empty; centred headline (`{typography.headline}`) "What are you stuck on?" + composer with mode pills + 3 example prompts (one CS, one maths, one SQL). |
| Empty — library | Library | "No lessons yet. Your first one is a question away." + New lesson button. |
| Empty — search | Library | "No lessons match "{q}"." + Clear search. |
| Empty — notes / practice | Panel tabs | One sentence + single action ("Add a note to step 3" / "Get 3 practice questions"). |
| Success | Generation done | Panel: "Lesson ready · 6 steps". Step 1 active; save status "Saved". No celebratory animation. |
| Save status | Panel header | Saved / Saving… / Couldn't save · Retry (auto-retry with backoff 3×, then manual). Unsaved changes on tab close → browser `beforeunload` prompt. |
| 409 conflict | Workspace | Inline alert (warning): "This board changed in another tab or device. Load newer version" (primary) · "Keep mine as a copy" (secondary, duplicates the Lesson with local Board). Never silently overwrite (AD-4). |
| Offline | Global banner | Warning banner under top bar: "You're offline. You can keep drawing; we'll save when you're back." Generation and follow-ups disabled with reason. Saves queue and flush on reconnect. |
| Allowance exhausted | Composer, indicator | Composer disabled for **new** lessons with message incl. reset time and countdown; current Lesson stays fully usable (step player, Board, notes) per UJ-2. Follow-ups that would charge show the same message. |
| At capacity (global ceiling) | Composer | Warning inline alert: "We're at capacity right now…" + Retry; no charge taken (AD-7). |
| Generation failed | Panel / composer | Danger inline alert: "That didn't come out right, so I left your Board as it was." + **Try again** (primary) + Details (request id). Allowance refund reflected. Board and prior Steps untouched (FR-6, FR-9). |
| Generation cancelled | Panel | Neutral note: "Stopped. Your Board is as it was." Composer text preserved for edit/resubmit. |
| Request too long | Composer | Counter turns danger; message "That's a bit long. Please keep it under {limit} characters." Submit disabled. |
| Not found | Workspace | "We couldn't find that lesson." + Go to library. Same for foreign and deleted ids (FR-16). |
| Session expired | Any | Dialog: "You've been signed out. Sign in to continue" — returns to the same route; unsaved Board kept locally until re-auth. |

## Interaction Primitives

**Keyboard map** (shown in a `?` shortcuts dialog). Shortcuts are disabled while focus is inside a text field or the Excalidraw canvas text editor; Board-scoped keys apply only when the Board has focus.

| Keys | Action |
|---|---|
| `N` | New lesson |
| `G` then `L` | Go to library |
| `/` | Focus composer (workspace) or search (library) |
| `Space` / `K` | Play / pause steps (when focus is on step bar or panel) |
| `J` / `L` or `←` / `→` on step bar | Previous / next Step |
| `Home` / `End` on step bar | First / last Step |
| `1`–`9` on step bar | Jump to Step n |
| `R` on step bar | Restart |
| `Esc` | Cancel generation; close dialog/sheet; leave Board focus to step bar |
| `Ctrl/⌘+Z`, `Ctrl/⌘+Shift+Z` | Undo / redo (Excalidraw, Board focus only) |
| `F6` | Cycle focus regions: sidebar → Board → step bar → panel → composer |
| `Ctrl/⌘+.` | Toggle explanation panel |
| `Ctrl/⌘+Shift+E` | Export dialog |
| `?` | Shortcuts help |

**Step controls:** Play auto-advances; Pause stops; any Board edit pauses. Jump renders that Step's Board state; AI elements from later Steps are hidden while viewing an earlier Step, learner elements always remain visible. `[ASSUMPTION]`

**Cancel generation:** Cancel button and `Esc` abort the request (client abort, AD-7); UI returns to prior state immediately and shows the cancelled note.

**Undo/redo:** Excalidraw history for Board edits. An applied AI Step is one undoable unit labelled in the undo history `[ASSUMPTION]`; undoing it does not delete the Step from the Lesson, only its Board elements until redo or re-jump.

**Board vs panel focus:** The Board is a single focus region; once inside, Excalidraw owns keys. `Esc` (with no Excalidraw selection/edit active) or `F6` exits to the step bar. Panel interactions never steal focus from the Board unless the learner moved there. When a new Step arrives, focus stays where it was; the change is announced instead.

**Touch:** one-finger draw/select per Excalidraw tool, two-finger pan/zoom; bottom sheet drags between peek / half / full; long-press an element for its origin badge and context menu. No hover-only affordances on touch.

## Accessibility Floor

- **WCAG 2.2 AA** on all core flows (sign-up, workspace, library, settings). Contrast is verified in `DESIGN.md` → Contrast verification.
- **Keyboard:** every control reachable and operable; logical tab order: skip link → top bar/sidebar → Board region → step bar → panel tabs → panel content → composer. Skip links: "Skip to Board", "Skip to explanation".
- **Focus:** always visible `{components.focus-ring}`; never obscured by the step bar or sheets (WCAG 2.4.11) — sheets reposition or scroll focused content into view.
- **Target size:** ≥ 24×24 CSS px everywhere; 44px on touch layouts.
- **Reduced motion:** `prefers-reduced-motion` or in-app setting → instant Steps, no animated pan/zoom, static thinking indicator (see `DESIGN.md` Motion).
- **Screen reader announcements** (one polite `aria-live` region for progress, one assertive for errors):
  - Generation: "Planning your lesson", "Step 2 of 6 ready", "Lesson ready, 6 steps", "Generation stopped", "Couldn't generate. Your board is unchanged. Try again button available."
  - Step change: "Step 3 of 7: Count the inner loop" followed by the Step explanation's first sentence; full text is reachable in the panel.
  - Save: announce only failures and recovery ("Couldn't save", "Saved again"), not every "Saved".
  - Allowance: announce when it drops to 1 and to 0.
- **Excalidraw limitation and alternative path:** the canvas is not screen-reader navigable and drawing is pointer-centric. Therefore the **explanation panel's Steps tab is the complete, equivalent text path**: every Step's explanation includes a text description of what was drawn (Board Operations carry alt text from the lesson schema `[ASSUMPTION]` add `alt` to `LessonStep`), math as accessible KaTeX (MathML), code as text. A learner can complete UJ-1 and UJ-2 entirely from the step bar + panel + composer without touching the canvas. Learner drawing is not required to use any feature; notes provide the text equivalent of learner annotation.
- **Forms:** labels always visible; errors inline, linked by `aria-describedby`, and summarised at top on submit. No CAPTCHA puzzles (WCAG 3.3.8); password fields allow paste and managers.
- **Text resize** to 200% and reflow at 320px width without loss (Board excepted, which zooms).
- **Theme:** both themes meet the same ratios; respects `forced-colors` mode with system colours for focus and borders.

## Responsive & Platform

| Breakpoint | Workspace behaviour |
|---|---|
| Laptop `≥ 1200px` | Sidebar (collapsible) · **Board centre** · explanation panel **right** (resizable 320–560px, collapsible) · step bar floating bottom-centre over the Board · composer at panel bottom |
| Tablet `768–1199px` | Sidebar → icon rail / sheet. Landscape: Board + right drawer panel (360px), step bar bottom. Portrait: Board top 60%, panel as bottom drawer 40% (draggable), step bar between them. Pencil/touch drawing first-class. |
| Phone `< 768px` | Top bar (menu, Lesson title, save status, overflow). **Board fills the screen**; **step bar** fixed above a **bottom sheet** panel (peek 96px shows current Step title + first line; half; full). Composer lives in the sheet; opening the keyboard expands the sheet to full. Library is a single-column list; settings single column. |

Reorganise, don't shrink (PRD §8.1). Responsive web only; no native apps in v1. Safe-area insets respected on phones. Orientation changes preserve the current Step and Board viewport.

## Inspiration & Anti-patterns

- **Lifted from good textbooks:** serif explanation at a reading measure, worked examples, one idea per Step.
- **Lifted from Excalidraw:** the hand-drawn learner layer, which is also our origin signal.
- **Lifted from video players:** play/pause/scrub step bar with predictable keys.
- **Rejected — chat-first layout:** the Board is the product, not a chat transcript with pictures.
- **Rejected — streaks, badges, time-on-site nudges** (SM-C1).
- **Rejected — revealing answers by default:** Hint and Practice make the learner try first (SM-C3).
- **Rejected — fake fallbacks / optimistic AI success:** failures are shown honestly (AD-11).

## Key Flows

### Sign-up with 18+ confirmation (FR-15, FR-18)

1. Visitor opens `/signup`: email, password (show/hide, strength hint), checkbox **"I confirm I am 18 or older"** (unchecked by default), link to the privacy notice ("What we send to our AI provider").
2. Submit without the checkbox → inline error on the checkbox: "You need to be 18 or older to use Whiteboard Tutor." Focus moves to it; nothing is sent.
3. Valid submit → account created, session started → workspace in empty "What are you stuck on?" state with allowance "5 of 5 lessons left today".
4. No social-login buttons unless configured. Errors: email in use → "That email already has an account. Sign in or reset your password." (no account-enumeration beyond what the backend allows `[ASSUMPTION]`).

### UJ-1. Maya, second-year CS student, learns Big-O from a sorting snippet (laptop)

1. Maya is signed in on a laptop; the workspace is empty. She clicks **New lesson** (or `N`).
2. She pastes her nested-loop code into the composer, picks **Explain**, presses `Enter`.
3. Panel: "Planning your lesson…" → "Drawing step 1 of 5…". The Board fills Step by Step: a code block (AI, clean lines, "Tutor"), loop annotations, a growth diagram. Explanations appear in serif in the panel; the step bar advances.
4. At Step 3 she presses `Space` to pause, types in the follow-up composer "why n² and not 2n?" (labelled "Asking about step 3").
5. **Climax:** Step 3 redraws on the Board with a worked iteration count (n × n table) highlighted in the Step wash; the panel replaces Step 3's explanation; screen readers hear "Step 3 updated". The rest of the Lesson is untouched. She sees it.
6. Resolution: save status "Saved". Next day she opens the Lesson from Library; it resumes at Step 3 with the same Board.
7. Edge: the AI returns a malformed step → danger inline alert "That didn't come out right, so I left your Board as it was." + **Try again**; allowance refunded; she retries successfully.

### UJ-2. Dev, first-year engineering student, solves a calculus problem and gets stuck (phone)

1. Dev, signed in on his phone at midnight, opens the menu → **New lesson**, types the derivative problem, picks **Solve**.
2. The Board fills the screen; the bottom sheet peeks with Step 1. He reads Step 1 (typeset with KaTeX; "Verified by calculation" on the computed coefficient).
3. Instead of Next, he taps **Hint** in the sheet: a hint appears for Step 2, without the answer. He tries, then taps **Simplify** on Step 2: only Step 2 is rewritten.
4. **Climax:** after a second hint, he writes the next line himself on the Board (hand-drawn, "You") and taps **"I've got it"**; the Step is marked "Completed by you" and the panel says "Nice — you worked that step out yourself."
5. Resolution: Lesson progress shows "2 of 4 steps completed by you".
6. Edge: his last hint used the final lesson of the day → indicator "0 of 5 left · resets 00:00 (in 23 min)". He can keep finishing this Lesson (step player, Board, notes); new lessons wait, and the composer explains the reset time.

### UJ-3. Priya, bootcamp learner, edits the Board and practises (tablet)

1. Priya, on a tablet in landscape, opens **Library**, searches "joins", opens her saved SQL Lesson. It resumes at her last Step.
2. With the pen she draws her own arrows between two tables (terracotta, hand-drawn, "You") and adds a note on Step 2 in the Notes tab.
3. She asks a follow-up on Step 2: "show a left join with a missing row".
4. **Climax:** the tutor redraws Step 2's tables with the missing row highlighted; **her arrows remain exactly where she drew them** (AD-3). "Show who drew what" confirms: her arrows still say "You".
5. She opens the **Practice** tab and taps "Get 3 practice questions", answers each, sees explanations.
6. Resolution: the Practice tab shows "3 attempts saved" with her answers; Library card shows the Lesson's practice count.
7. Edge: she had the Lesson open on her laptop too → 409 conflict alert on the tablet: "Load newer version" or "Keep mine as a copy".

## UX Design Requirements

Actionable items for story acceptance criteria. Token paths refer to `DESIGN.md`.

- **UX-DR1** Generate CSS custom properties from every `DESIGN.md` token (colors light + dark, typography, spacing, rounded, motion, elevation); no hard-coded hex values in components (lint rule).
- **UX-DR2** Theme defaults to `prefers-color-scheme`; Settings offers System / Light / Dark, persisted to the user's preferences and applied before first paint (no flash). Excalidraw `theme` prop follows the active theme.
- **UX-DR3** All text/background pairs used in the UI meet the ratios recorded in `DESIGN.md` Contrast verification; an automated contrast test (axe or token test) runs in CI for both themes.
- **UX-DR4** Fonts: Source Serif 4 (explanation/headings), Source Sans 3 (UI), JetBrains Mono (code, ligatures off), KaTeX for math; self-hosted with `font-display: swap` and the system fallback stacks in `{typography.*}`.
- **UX-DR5** App shell: collapsible sidebar (`{spacing.sidebar-width}` ↔ `{spacing.sidebar-collapsed}`, state remembered), "New lesson" primary action at top, Library, Settings, allowance indicator in footer; icon rail/sheet on tablet; top bar + sheet on phone.
- **UX-DR6** Workspace layout per breakpoint: laptop Board centre + right panel (resizable 320–560px, collapsible with `Ctrl/⌘+.`); tablet drawer; phone full-screen Board + step bar + bottom sheet (peek/half/full).
- **UX-DR7** Board origin distinction uses four cues: AI roughness 0 + normal font + `ai-ink`; Learner roughness 1 + Excalifont + `learner-ink`; origin badge ("Tutor"/"You") on select/hover/long-press; "Show who drew what" toggle. Accessible name includes origin.
- **UX-DR8** Step bar with Restart, Previous, Play/Pause, Next, step-dot buttons and a visible "Step n of N" label; keyboard map per Interaction Primitives; jump renders that Step's Board state; any learner Board edit pauses Play.
- **UX-DR9** Explanation panel tabs Steps · Notes · Practice · Summary; current Step highlighted with `{colors.light.highlight}` wash and `primary` rule; selecting a Step in the panel jumps the Board.
- **UX-DR10** Request composer with mode radio group, live character counter (warning at 90%, danger over limit, submit disabled), `Enter` submit / `Shift+Enter` newline, Cancel replacing submit while generating, `Esc` cancels.
- **UX-DR11** Generation states implemented exactly per State Patterns: planning, drawing step n of N, ready, cancelled (composer text preserved), failed (inline alert with Try again + request-id details, Board unchanged), never a fabricated fallback.
- **UX-DR12** Allowance indicator shows "x of y lessons left today" and reset time with countdown; turns `warning` at 1; at 0 disables new-lesson submit with reset time while the current Lesson stays usable; at-capacity shows its own warning alert.
- **UX-DR13** Save status in panel header (Saved / Saving… / Couldn't save · Retry) with 3 automatic retries; offline banner queues saves; `beforeunload` guard with unsaved changes.
- **UX-DR14** 409 conflict alert offers "Load newer version" and "Keep mine as a copy"; never silently overwrites.
- **UX-DR15** Code blocks and math have Copy buttons (raw source / LaTeX) that announce "Copied"; "Verified" mark shown only when the server flags `verified=true`.
- **UX-DR16** Library: debounced search (250 ms), filter chips (All, Archived, by mode), "Load more" pagination, card overflow menu (Rename inline, Duplicate, Archive, Export, Delete with confirm dialog defaulting focus to Keep).
- **UX-DR17** Export dialog offers Board image (PNG, SVG) and Lesson file; reachable from workspace overflow, library card and `Ctrl/⌘+Shift+E`.
- **UX-DR18** Practice tab: one question at a time, Check reveals explanation, "Show answer" requires a second confirmation, attempts listed and persisted.
- **UX-DR19** Notes tab: plain-text note per Step, autosaved with save status; Summary tab shows key takeaways with a Generate action subject to allowance.
- **UX-DR20** Sign-up: unchecked "I confirm I am 18 or older" checkbox required, inline error and focus on failure, privacy-notice link; no social login unless configured; password reset via email request + set-new pages.
- **UX-DR21** Settings: theme, reduce motion, password change, sign out, Delete account (dialog requiring email + password; explains all data is removed); privacy notice page names the AI provider and what is sent.
- **UX-DR22** Visible 2px focus ring (`{components.focus-ring}`) on all focusables incl. Excalidraw toolbar; skip links "Skip to Board" / "Skip to explanation"; `F6` cycles regions; focus never obscured by sticky bars or sheets.
- **UX-DR23** Live regions: polite for generation progress and step changes ("Step 3 of 7: {title}"), assertive for errors; save success not announced, failures are.
- **UX-DR24** Every Step's panel text includes a description of its Board change so a learner can follow a Lesson without the canvas (requires `alt` text per Step in the lesson schema).
- **UX-DR25** Reduced motion (OS or in-app) → instant Steps, no animated pan/zoom, static thinking indicator, transitions ≤ 120ms opacity-only; default motion uses `{motion.*}` tokens.
- **UX-DR26** Targets ≥ 24×24 px everywhere and ≥ 44px on touch layouts; reflow at 320px and 200% text without loss (Board excepted).
- **UX-DR27** Microcopy follows Voice and Tone: errors state what happened, what is safe, the next action; no emojis, streaks or celebratory animation.
- **UX-DR28** Not-found page identical for foreign and deleted Lesson ids; session-expiry dialog returns to the same route after sign-in.

## Assumptions & Gaps

- `[ASSUMPTION]` Radix UI (or equivalent headless library) — confirm at Story 1.1.
- `[ASSUMPTION]` Origin badge overlay and per-element roughness/font defaults are feasible in Excalidraw 0.18 via `customData.origin`; verify at Story 2.2.
- `[ASSUMPTION]` Lesson schema gains a per-Step `alt` description for the text path (UX-DR24) — needs an architecture/schema update (AD-2/AD-9).
- `[ASSUMPTION]` "I've got it" learner-completed Step marker (UJ-2 climax) needs a Step completion field; not explicit in PRD FRs.
- `[ASSUMPTION]` Autosave debounce 1.5 s, Play pace, routes and the "Show who drew what" toggle are proposals.
- Gap: epics.md has no story for theme toggle/settings preferences or the shortcuts dialog; Story 7.2 or a new story should absorb UX-DR2, UX-DR22.
