---
title: Whiteboard Tutor — Design System
name: Whiteboard Tutor
description: Calm, focused study room for a whiteboard-first AI tutor. Warm paper and deep ink, soft accents, generous reading type, quiet motion. The Board is the star.
status: final
created: 2026-10-28
updated: 2026-10-29
sources:
  - _bmad-output/planning-artifacts/prds/prd-Solvely.ai-2026-10-27/prd.md
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/architecture/architecture-Solvely.ai-2026-10-27/ARCHITECTURE-SPINE.md
companion: EXPERIENCE.md
colors:
  # Two complete named sets. Each key becomes one CSS custom property
  # (--color-<key>) whose value is swapped by theme: [data-theme="light"|"dark"],
  # defaulting to prefers-color-scheme. Component tokens below reference the
  # light set by path; the dark set resolves through the same CSS variable.
  light:
    paper: '#FAF7F2'            # app background
    surface: '#F3EEE5'          # sidebar, panel wells
    surface-raised: '#FFFFFF'   # cards, dialogs, sheets, inputs
    surface-subtle: '#E8E1D5'   # hover fill, selected row, chips
    board: '#FFFDF8'            # Excalidraw canvas background
    ink: '#1F2430'              # primary text
    ink-muted: '#555C69'        # secondary text, captions, placeholders
    border: '#E2DACD'           # decorative dividers only (non-essential)
    border-strong: '#8C8374'    # input and control boundaries (>=3:1)
    primary: '#2F4B7C'          # ink-blue: primary actions, links, active nav
    on-primary: '#FFFFFF'
    accent: '#5C7A68'           # sage: progress, current-step marker (non-text)
    ai-ink: '#2F5D8A'           # AI Content stroke and text on the Board
    learner-ink: '#A34E2A'      # Learner Content default stroke (terracotta)
    highlight: '#F5E6B8'        # Step highlight wash behind AI elements / text
    focus: '#2F6FB0'            # focus ring
    success: '#2E6B47'
    warning: '#8A5A00'
    danger: '#B3261E'
    on-danger: '#FFFFFF'
    scrim: 'rgba(31, 36, 48, 0.40)'
  dark:
    paper: '#171A21'
    surface: '#1E222B'
    surface-raised: '#262B36'
    surface-subtle: '#2E3440'
    board: '#1B1F27'
    ink: '#ECE7DE'
    ink-muted: '#A9A398'
    border: '#30353F'
    border-strong: '#6F7684'
    primary: '#9DB8E8'
    on-primary: '#12161D'
    accent: '#9CBFA8'
    ai-ink: '#8FB3E0'
    learner-ink: '#E59A72'
    highlight: '#4A4025'
    focus: '#A8C7FA'
    success: '#8CCB9F'
    warning: '#E6B85C'
    danger: '#F2948C'
    on-danger: '#12161D'
    scrim: 'rgba(0, 0, 0, 0.55)'
typography:
  # Reading voice: Source Serif 4 (explanations). UI voice: Source Sans 3.
  # Code: JetBrains Mono. Math: KaTeX fonts. All Google Fonts, self-hosted
  # via the build with font-display: swap. [ASSUMPTION]
  display:
    fontFamily: "'Source Serif 4', 'Iowan Old Style', Georgia, serif"
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.01em
  headline:
    fontFamily: "'Source Serif 4', 'Iowan Old Style', Georgia, serif"
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  title:
    fontFamily: "'Source Sans 3', 'Segoe UI', system-ui, sans-serif"
    fontSize: 18px
    fontWeight: '600'
    lineHeight: '1.4'
  explanation:
    fontFamily: "'Source Serif 4', 'Iowan Old Style', Georgia, serif"
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.65'
  explanation-mobile:
    fontFamily: "'Source Serif 4', 'Iowan Old Style', Georgia, serif"
    fontSize: 17px
    fontWeight: '400'
    lineHeight: '1.6'
  body:
    fontFamily: "'Source Sans 3', 'Segoe UI', system-ui, sans-serif"
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  label:
    fontFamily: "'Source Sans 3', 'Segoe UI', system-ui, sans-serif"
    fontSize: 14px
    fontWeight: '600'
    lineHeight: '1.4'
  caption:
    fontFamily: "'Source Sans 3', 'Segoe UI', system-ui, sans-serif"
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.4'
  code:
    fontFamily: "'JetBrains Mono', ui-monospace, 'Cascadia Code', Menlo, Consolas, monospace"
    fontSize: 15px
    fontWeight: '400'
    lineHeight: '1.55'
  math:
    fontFamily: 'KaTeX_Main, serif'
    note: 'Rendered by KaTeX at 1.1em of the surrounding text'
rounded:
  sm: 4px
  DEFAULT: 6px
  md: 8px
  lg: 12px
  full: 9999px
spacing:
  '1': 4px
  '2': 8px
  '3': 12px
  '4': 16px
  '5': 20px
  '6': 24px
  '8': 32px
  '10': 40px
  '12': 48px
  '16': 64px
  gutter-mobile: 16px
  gutter-desktop: 24px
  panel-width: 400px
  panel-width-min: 320px
  sidebar-width: 248px
  sidebar-collapsed: 56px
  reading-measure: 66ch
  touch-target: 44px
motion:
  duration-quick: 120ms
  duration-calm: 220ms
  duration-step: 360ms
  easing: 'cubic-bezier(0.2, 0, 0, 1)'
  reduced: 'all durations 0ms except opacity fades capped at 120ms; no transforms, no auto-pan animation'
elevation:
  flat: 'none'
  raised: '0 1px 2px rgba(31, 36, 48, 0.06), 0 2px 8px rgba(31, 36, 48, 0.06)'
  overlay: '0 8px 32px rgba(31, 36, 48, 0.14)'
  dark-note: 'In dark theme shadows are replaced by surface-raised tone plus a 1px {colors.dark.border} outline'
components:
  button-primary:
    background: '{colors.light.primary}'
    foreground: '{colors.light.on-primary}'
    radius: '{rounded.DEFAULT}'
    height: 40px
    paddingX: '{spacing.4}'
    typography: '{typography.label}'
  button-secondary:
    background: '{colors.light.surface-raised}'
    foreground: '{colors.light.ink}'
    border: '1px solid {colors.light.border-strong}'
    radius: '{rounded.DEFAULT}'
    height: 40px
  button-ghost:
    background: 'transparent'
    foreground: '{colors.light.ink}'
    hover: '{colors.light.surface-subtle}'
    radius: '{rounded.DEFAULT}'
  button-danger:
    background: '{colors.light.danger}'
    foreground: '{colors.light.on-danger}'
    radius: '{rounded.DEFAULT}'
  icon-button:
    size: '{spacing.touch-target}'
    radius: '{rounded.DEFAULT}'
    foreground: '{colors.light.ink}'
  input:
    background: '{colors.light.surface-raised}'
    foreground: '{colors.light.ink}'
    border: '1px solid {colors.light.border-strong}'
    radius: '{rounded.DEFAULT}'
    height: 44px
    placeholder: '{colors.light.ink-muted}'
  focus-ring:
    outline: '2px solid {colors.light.focus}'
    offset: 2px
  request-composer:
    background: '{colors.light.surface-raised}'
    border: '1px solid {colors.light.border-strong}'
    radius: '{rounded.lg}'
    typography: '{typography.body}'
  mode-selector:
    background: '{colors.light.surface}'
    selected-background: '{colors.light.primary}'
    selected-foreground: '{colors.light.on-primary}'
    radius: '{rounded.full}'
  explanation-panel:
    background: '{colors.light.surface}'
    width: '{spacing.panel-width}'
    typography: '{typography.explanation}'
    measure: '{spacing.reading-measure}'
  step-bar:
    background: '{colors.light.surface-raised}'
    current-marker: '{colors.light.accent}'
    radius: '{rounded.lg}'
    height: 56px
  step-dot:
    size: 10px
    done: '{colors.light.accent}'
    current-ring: '2px solid {colors.light.primary}'
    upcoming: '{colors.light.border-strong}'
  board-ai-element:
    stroke: '{colors.light.ai-ink}'
    strokeStyle: 'solid'
    roughness: 0
    fontFamily: 'Excalidraw Nunito (normal)'
    origin-badge: 'Tutor'
  board-learner-element:
    stroke: '{colors.light.learner-ink}'
    strokeStyle: 'solid'
    roughness: 1
    fontFamily: 'Excalifont (hand-drawn)'
    origin-badge: 'You'
  board-step-highlight:
    background: '{colors.light.highlight}'
    outline: '2px dashed {colors.light.ai-ink}'
  origin-badge:
    typography: '{typography.caption}'
    radius: '{rounded.full}'
    ai-foreground: '{colors.light.ai-ink}'
    learner-foreground: '{colors.light.learner-ink}'
    background: '{colors.light.surface-raised}'
  code-block:
    background: '{colors.light.surface}'
    foreground: '{colors.light.ink}'
    typography: '{typography.code}'
    radius: '{rounded.md}'
  verified-mark:
    foreground: '{colors.light.success}'
    typography: '{typography.caption}'
  allowance-meter:
    track: '{colors.light.surface-subtle}'
    fill: '{colors.light.accent}'
    typography: '{typography.caption}'
  save-status:
    typography: '{typography.caption}'
    foreground: '{colors.light.ink-muted}'
    failed-foreground: '{colors.light.danger}'
  inline-alert:
    background: '{colors.light.surface-raised}'
    border-left: '4px solid (role colour: danger | warning | success | primary)'
    radius: '{rounded.md}'
  card-lesson:
    background: '{colors.light.surface-raised}'
    radius: '{rounded.md}'
    shadow: '{elevation.raised}'
  dialog:
    background: '{colors.light.surface-raised}'
    radius: '{rounded.lg}'
    shadow: '{elevation.overlay}'
    scrim: '{colors.light.scrim}'
  bottom-sheet:
    background: '{colors.light.surface-raised}'
    radius: '{rounded.lg} {rounded.lg} 0 0'
    handle: '{colors.light.border-strong}'
  sidebar:
    background: '{colors.light.surface}'
    width: '{spacing.sidebar-width}'
    collapsed-width: '{spacing.sidebar-collapsed}'
    active-item: '{colors.light.surface-subtle}'
    active-indicator: '{colors.light.primary}'
---

## Brand & Style

Whiteboard Tutor is a **calm, focused study room**. The learner arrives stuck, often late at night, often anxious about an exam. The interface must lower the pulse: warm paper instead of clinical white, deep ink instead of pure black, one quiet blue for action, and type set for *reading*, not scanning.

**The Board is the star.** Every layout decision gives the Excalidraw Board the largest, calmest area on screen. Chrome (sidebar, panel, step bar) is tonal and recessive; it never competes with what is drawn. The explanation panel reads like a good textbook margin: serif, generous leading, a comfortable measure.

Posture: *quiet confidence*. No gradients, no mascots, no confetti, no streaks. Motion exists only to explain change (a Step arriving on the Board), never to decorate. `[ASSUMPTION]` The working title and identity are open (PRD §9 Q1); this system carries no logo-dependent colours, so a name change does not break it.

## Colors

Two complete named sets, `colors.light` and `colors.dark`. Theme follows the device (`prefers-color-scheme`) by default; Account settings offers **System / Light / Dark**, stored as a user preference and applied via `[data-theme]` on `<html>` before first paint (no flash).

| Role | Light | Dark | Use | Not for |
|---|---|---|---|---|
| `paper` | `#FAF7F2` | `#171A21` | App background | Board canvas |
| `surface` | `#F3EEE5` | `#1E222B` | Sidebar, explanation panel, code wells | Primary buttons |
| `surface-raised` | `#FFFFFF` | `#262B36` | Cards, dialogs, sheets, inputs | Large page areas |
| `surface-subtle` | `#E8E1D5` | `#2E3440` | Hover, selected row, chips | Text |
| `board` | `#FFFDF8` | `#1B1F27` | Excalidraw `viewBackgroundColor` | Chrome |
| `ink` | `#1F2430` | `#ECE7DE` | All primary text | — |
| `ink-muted` | `#555C69` | `#A9A398` | Captions, placeholders, metadata | Body paragraphs |
| `border` | `#E2DACD` | `#30353F` | Decorative dividers only | Input/control edges |
| `border-strong` | `#8C8374` | `#6F7684` | Input, checkbox, control boundaries | Decoration |
| `primary` | `#2F4B7C` | `#9DB8E8` | Primary buttons, links, active nav, current Step ring | Status meaning |
| `accent` (sage) | `#5C7A68` | `#9CBFA8` | Step progress, allowance fill (non-text only) | Text, errors |
| `ai-ink` | `#2F5D8A` | `#8FB3E0` | AI Content stroke/text on Board; "Tutor" badge | Learner Content |
| `learner-ink` | `#A34E2A` | `#E59A72` | Default Learner stroke; "You" badge | AI Content |
| `highlight` | `#F5E6B8` | `#4A4025` | Current-Step wash on the Board and in the panel | Errors |
| `focus` | `#2F6FB0` | `#A8C7FA` | Focus ring only | Fills |
| `success` | `#2E6B47` | `#8CCB9F` | Saved, verified mark, correct answer | Decoration |
| `warning` | `#8A5A00` | `#E6B85C` | Allowance low, offline, at capacity | Errors |
| `danger` | `#B3261E` | `#F2948C` | Errors, destructive actions | Warnings |

**Board colour discipline.** The Excalidraw colour picker is restricted to a curated palette that includes `ai-ink`-adjacent blues only for the tutor; Learners may still pick any colour, which is exactly why origin is never signalled by colour alone (see Components → Board elements). When the theme switches, Excalidraw's own `theme` prop switches with it; element colours authored in light are rendered through Excalidraw's dark-mode filter, so the tutor emits semantic colours that are legible under both. `[ASSUMPTION]` verify Excalidraw 0.18 dark filter on `ai-ink`/`learner-ink` at Story 2.2.

### Contrast verification (WCAG 2.2 AA)

Computed with the WCAG 2.x relative-luminance formula (script run 2026-10-28). Thresholds: text ≥ 4.5:1, large text / UI components / focus indicator ≥ 3:1.

| Pair | Light | Dark | Need |
|---|---|---|---|
| `ink` on `paper` | 14.52 | 14.14 | 4.5 |
| `ink` on `surface` | 13.43 | 12.93 | 4.5 |
| `ink` on `surface-raised` | 15.52 | 11.51 | 4.5 |
| `ink` on `board` | 15.26 | 13.41 | 4.5 |
| `ink` on `highlight` | 12.48 | 8.31 | 4.5 |
| `ink` on `surface-subtle` | 11.94 | 10.14 | 4.5 |
| `ink-muted` on `paper` | 6.30 | 6.95 | 4.5 |
| `ink-muted` on `surface` | 5.82 | 6.35 | 4.5 |
| `ink-muted` on `surface-raised` | 6.73 | 5.66 | 4.5 |
| `ink-muted` on `surface-subtle` | 5.18 | 4.98 | 4.5 |
| `on-primary` on `primary` | 8.68 | 9.03 | 4.5 |
| `primary` (link) on `paper` | 8.13 | 8.67 | 4.5 |
| `primary` on `surface` | 7.51 | 7.93 | 4.5 |
| `ai-ink` on `board` | 6.76 | 7.62 | 4.5 |
| `learner-ink` on `board` | 5.61 | 7.23 | 4.5 |
| `ai-ink` on `paper` | 6.44 | 8.04 | 4.5 |
| `learner-ink` on `paper` | 5.34 | 7.62 | 4.5 |
| `danger` on `paper` | 6.12 | 7.79 | 4.5 |
| `danger` on `surface-raised` | 6.54 | 6.34 | 4.5 |
| `on-danger` on `danger` | 6.54 | 8.11 | 4.5 |
| `warning` on `paper` | 5.55 | 9.43 | 4.5 |
| `warning` on `surface-raised` | 5.93 | 7.68 | 4.5 |
| `success` on `paper` | 5.94 | 9.25 | 4.5 |
| `success` on `surface-raised` | 6.34 | 7.53 | 4.5 |
| `focus` on `paper` | 4.89 | 10.13 | 3.0 |
| `focus` on `surface` | 4.52 | 9.26 | 3.0 |
| `focus` on `surface-raised` | 5.22 | 8.25 | 3.0 |
| `focus` on `board` | 5.14 | 9.60 | 3.0 |
| `border-strong` on `paper` | 3.50 | 3.81 | 3.0 |
| `border-strong` on `surface-raised` | 3.74 | 3.11 | 3.0 |
| `accent` (non-text) on `paper` | 4.43 | 8.65 | 3.0 |

**Lowest ratios:** light 3.50 (`border-strong` on `paper`, UI boundary); dark 3.11 (`border-strong` on `surface-raised`, UI boundary). Lowest *text* ratios: light 5.18, dark 4.98 (`ink-muted` on `surface-subtle`). All pass. `border` (decorative) is intentionally below 3:1 and must never be the only boundary of an interactive control.

## Typography

Three voices, one rule: *explanations are read, UI is scanned, code is copied.*

- **Explanation — Source Serif 4**, `{typography.explanation}` 18px / 1.65 (17px / 1.6 on phones), capped at `{spacing.reading-measure}` (66ch). Used for Step explanations, follow-up answers, summaries, practice explanations. A humane serif makes long reasoning feel like a textbook, not a chat log.
- **UI — Source Sans 3**, `{typography.body}` 16px for controls, lists, forms; `{typography.label}` 14px/600 for buttons and field labels; `{typography.caption}` 13px for metadata (never below 13px; never for essential instructions).
- **Headings** — `{typography.display}` 32px and `{typography.headline}` 24px in Source Serif 4, used for page titles (Library, Settings), Lesson titles and empty-state headlines only.
- **Code — JetBrains Mono**, `{typography.code}` 15px / 1.55 with tabular figures; ligatures **off** (learners must see `!=` literally).
- **Math — KaTeX**, at 1.1em of surrounding text; display equations centred with `{spacing.4}` vertical breathing room.

Fallbacks are system stacks (Georgia / Segoe UI / Consolas) so a font-loading failure never blocks reading. User text scaling to 200% must not clip any surface. Board text uses Excalidraw fonts (see Components) and is not governed by this ramp.

## Layout & Spacing

4px base; the scale `{spacing.1}`…`{spacing.16}` (4 → 64px). Generous by default: panel padding `{spacing.6}`, gap between explanation paragraphs `{spacing.4}`, section gaps `{spacing.8}`.

| Breakpoint | Layout |
|---|---|
| `≥ 1200px` laptop | Sidebar (`{spacing.sidebar-width}`, collapsible to `{spacing.sidebar-collapsed}`) · Board centre (flex, min 60% of remaining width) · Explanation panel right (`{spacing.panel-width}`, resizable 320–560px) · Step bar floats bottom-centre over the Board |
| `768–1199px` tablet | Sidebar collapsed to icons (sheet on demand) · Board full width · panel as right-side drawer (landscape) or bottom drawer at 40% height (portrait) · Step bar pinned bottom |
| `< 768px` phone | Top bar with menu · Board fills viewport · Step bar fixed above a bottom sheet (peek 96px / half / full) holding the explanation and composer |

Gutters: `{spacing.gutter-desktop}` 24px, `{spacing.gutter-mobile}` 16px. All touch targets ≥ `{spacing.touch-target}` (44px) on touch layouts, ≥ 24×24 CSS px everywhere (WCAG 2.5.8). Non-Board pages (Library, Settings, auth) use a single centred column, max 960px (library grid) or 560px (forms).

## Elevation & Depth

Depth through **tonal layering**, not shadows: `paper` → `surface` → `surface-raised`. Shadows are rare and soft: `{elevation.raised}` on lesson cards and the floating step bar; `{elevation.overlay}` on dialogs, menus and the bottom sheet. In dark theme shadows are dropped; raised elements use the `surface-raised` tone plus a 1px `{colors.dark.border}` edge. The Board itself is flat: no shadow, no frame, so it reads as the room's wall.

## Shapes

Soft, not bubbly: `{rounded.sm}` 4px for chips and checkboxes, `{rounded.DEFAULT}` 6px for buttons and inputs, `{rounded.md}` 8px for cards and code blocks, `{rounded.lg}` 12px for dialogs, the composer, the step bar and the bottom sheet's top corners. `{rounded.full}` only for the mode selector pills, origin badges and step dots.

## Components

Built from headless accessible primitives (e.g. Radix UI) styled with CSS variables generated from these tokens. Visual specs only; behaviour lives in `EXPERIENCE.md`.

- **Buttons** — primary (`{colors.light.primary}` fill), secondary (raised + `border-strong` outline), ghost (transparent, `surface-subtle` hover), danger (`{colors.light.danger}` fill; used only inside confirmation dialogs). 40px tall (44px on touch). One primary per surface region.
- **Focus ring** — `2px solid {colors.light.focus}` with 2px offset on every focusable element, including Excalidraw toolbar buttons (override its CSS), step dots and panel tabs. Never removed; `:focus-visible` only.
- **Request composer** — multi-line textarea with `{rounded.lg}` corners, a mode selector row above (pills: Explain · Solve · Hint · Simplify · Practice), a character counter (`caption`, turns `warning` at 90%, `danger` over the limit) and a primary "Teach me" button. While generating, the button becomes secondary "Cancel".
- **Explanation panel** — `surface` background; header with Lesson title (headline) + save status; tabs **Steps · Notes · Practice · Summary**; body in `{typography.explanation}`. The current Step's text sits on a `{colors.light.highlight}` wash with a 3px `primary` left rule.
- **Step bar** — raised, `{rounded.lg}`, 56px: Restart · Previous · Play/Pause · Next, a step-dot rail (done = `accent` fill, current = `primary` ring, upcoming = `border-strong` outline) and "Step 3 of 7" text. Dots are never the only indicator; the text label is always present.
- **Board elements (AI vs Learner)** — distinguished by **four** independent cues, never colour alone:
  1. **Stroke character:** AI Content uses roughness 0 (clean, architect lines); Learner Content keeps Excalidraw's hand-drawn roughness 1.
  2. **Typeface:** AI text uses Excalidraw's normal (Nunito) font; Learner text defaults to Excalifont (handwritten).
  3. **Origin badge:** selecting or hovering an element shows a small pill — "Tutor" (`ai-ink`) or "You" (`learner-ink`) — and the element's accessible name includes the origin.
  4. **Colour:** default `ai-ink` vs `learner-ink`.
  A Board toolbar toggle **"Show who drew what"** labels every element group with its badge at once. `[ASSUMPTION]` badge rendering via an overlay layer driven by `customData.origin` (AD-3); verify feasibility in Story 2.2.
- **Step highlight on Board** — the current Step's AI elements get a `{colors.light.highlight}` backing rectangle and a 2px dashed `ai-ink` outline; prior Steps' AI elements stay at full opacity (never fade text below contrast).
- **Code block** — `surface` well, `{typography.code}`, `{rounded.md}`, language label top-left, "Copy" ghost button top-right. Long lines scroll horizontally inside the block, never the page.
- **Math** — KaTeX render with a "Copy LaTeX" ghost button on hover/focus.
- **Verified mark** — check glyph + text "Verified" in `success`, caption size, with a tooltip "Checked by calculation, not by the AI." Unverified results show nothing (no "unverified" warning noise).
- **Allowance indicator** — sidebar footer (laptop) / account menu (phone): "3 of 5 lessons left today" text plus a 4px `accent` meter; at 1 left the text turns `warning`; at 0 it reads "Resets at 00:00 (in 5 h)".
- **Save status** — caption text with icon in the panel header: "Saved" (`ink-muted`), "Saving…" (`ink-muted`), "Couldn't save — Retry" (`danger`, Retry is a link button).
- **Inline alert** — raised card with 4px left rule in role colour, icon + title (`label`) + body (`body`) + optional action. Used for generation errors, at-capacity, offline, conflict.
- **Lesson card** — raised, `{rounded.md}`, `{elevation.raised}`; title (`title`), mode chip, last-opened date (`caption`), progress "Step 3 of 7", overflow menu.
- **Dialog / bottom sheet / menus** — `{rounded.lg}`, `{elevation.overlay}`, `scrim` backdrop. Destructive dialogs put the danger button on the right and the safe "Keep" option as default focus.
- **Sidebar** — `surface`; items 40px with icon + label; active item `surface-subtle` fill + 3px `primary` left indicator; "New lesson" primary button at top.

### Motion

Quiet and explanatory. `{motion.duration-step}` 360ms ease for a Step's elements fading/drawing in; `{motion.duration-calm}` 220ms for panels, sheets, drawers; `{motion.duration-quick}` 120ms for hover/press. No bouncing, no parallax, no looping animation except a slow (1.6s) opacity pulse on the "Thinking…" indicator. **Reduced motion** (`prefers-reduced-motion: reduce`, or the in-app "Reduce motion" setting): Steps appear instantly, viewport jumps instead of animated pan/zoom, the thinking pulse becomes a static indicator with text, and all transitions drop to ≤120ms opacity-only.

## Do's and Don'ts

| Do | Don't |
|---|---|
| Give the Board the largest, calmest area on every layout | Wrap the Board in cards, frames or shadows |
| Set explanations in Source Serif 4 at 18px within 66ch | Set long explanations in 14px sans or full-width |
| Mark AI vs Learner Content by stroke, typeface, badge *and* colour | Rely on colour alone for origin, Step state or errors |
| Use `border-strong` for every interactive control edge | Use decorative `border` as a control's only boundary |
| Keep one `primary` action per region | Use `accent` sage for text or for actions |
| Show a visible 2px `focus` ring everywhere, including the Board toolbar | Remove outlines or use focus colours below 3:1 |
| Animate only to explain a change; honour reduced motion | Decorate with confetti, streaks or looping motion |
| Specify every new token in both `colors.light` and `colors.dark` | Ship a colour that has only a light value |
