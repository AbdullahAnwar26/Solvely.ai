---
title: 'Story 1.1: Web app shell and API client'
type: 'feature'
created: '2026-10-29'
status: 'done'
baseline_commit: '1521f88'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-1-context.md'
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-Solvely.ai-2026-10-27/ARCHITECTURE-SPINE.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Solvely.ai-2026-10-28/DESIGN.md'
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-Solvely.ai-2026-10-28/EXPERIENCE.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There is no web app. Every later UI story needs a typed, tested React foundation that follows the UX contract and talks to the API through a client generated from its OpenAPI schema.

**Approach:** Scaffold `apps/web` (React 19 + TypeScript strict + Vite) with lint, type-check, Vitest and build commands; apply the DESIGN.md tokens as CSS variables following the device light/dark setting; build a responsive app shell (collapsible sidebar, content area, router); and generate typed API client code from the backend OpenAPI schema into `packages/shared`.

## Boundaries & Constraints

**Always:** TypeScript `strict`. Before pinning, verify that the chosen TypeScript major works with the installed Vite, Vitest, typescript-eslint and React plugin (registry latest of TypeScript was 7.0.2 and is unverified); if it does not, pin the newest major that does and record the reason in Implementation Notes. Pin dependency versions exactly and commit the lockfile. npm workspaces from the repo root (`apps/web`, `packages/shared`). Tokens come from DESIGN.md (both light and dark sets), exposed as `--color-*`, typography and spacing CSS custom properties, theme chosen by `prefers-color-scheme` (manual toggle is Story 1.6) and `[data-theme]` override supported in CSS. Fonts self-hosted through the build (no runtime third-party requests). Shell: skip-to-content link, semantic landmarks, collapsible sidebar (state remembered in `localStorage` inside try/catch), keyboard operable with visible focus ring using `{colors.focus}`, reduced-motion honoured, responsive across laptop, tablet and phone per EXPERIENCE.md. API client generated from `GET /api/v1/schema/` (committed generated types plus an npm script to regenerate); a small typed fetch wrapper sends `credentials: "include"`, reads the CSRF cookie into `X-CSRFToken` for unsafe methods, and turns error-envelope responses into a typed `ApiError`. Vite dev server proxies `/api` to `http://localhost:8000`. Lazy-load route components.

**Never:** No auth screens (Story 1.7), no theme toggle (Story 1.6), no "New lesson" button or any control without real behaviour, no lesson or board code, no Excalidraw, no fake data, no tokens in browser storage, no backend changes except if the schema needs a trivial fix (report it).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Shell renders | open `/` at 1280, 820, 390 px | landmarks present; sidebar docked, collapsible, or drawer by breakpoint | N/A |
| Keyboard | Tab from page load | first stop is skip link; focus order sidebar toggle, nav, main; visible focus ring | N/A |
| Collapse persists | collapse sidebar, reload | state restored | storage unavailable -> default state, no crash |
| Unknown route | `/nope` | accessible not-found page with link home | N/A |
| Theme | OS dark / light | correct token set applied, no flash of wrong theme | N/A |
| Reduced motion | `prefers-reduced-motion: reduce` | no transitions/animations | N/A |
| API success | typed GET `/api/v1/health/` | typed result | N/A |
| API error | non-2xx with envelope | throws `ApiError` with code, message, retryable, request_id, fields | non-envelope body -> generic ApiError |
| CSRF | unsafe request with `csrftoken` cookie | `X-CSRFToken` header set, credentials included | missing cookie -> request still sent |
| Schema drift | regenerate script | types regenerate from live schema deterministically | script fails with clear message if API unreachable |

</frozen-after-approval>

## Code Map

- `package.json` (root) -- new: npm workspaces, shared scripts (`lint`, `typecheck`, `test`, `build`, `gen:api`).
- `apps/web/` -- new: Vite React TS app (`src/main.tsx`, `src/app/` router and shell, `src/styles/tokens.css` from DESIGN.md, `src/api/client.ts` wrapper, tests beside code).
- `packages/shared/` -- new: generated OpenAPI types (`openapi-typescript` or equivalent, version verified), exports.
- `apps/api` -- read-only except the schema endpoint `/api/v1/schema/`.
- `.github/workflows/` -- do not add CI here (Story 7.3).
- `docs/ARCHITECTURE_NOTES.md` -- add a short "web app conventions" note (commands, token usage, how to regenerate API types).

## Tasks & Acceptance

**Execution:**
- [x] root `package.json`, `.gitignore` additions -- workspaces, scripts, node_modules/dist ignored
- [x] `apps/web` scaffold -- Vite, React 19, TS strict, ESLint, Vitest + React Testing Library, router, lazy routes
- [x] `src/styles/tokens.css` + base styles -- both token sets, fonts, focus ring, reduced motion
- [x] app shell components -- skip link, collapsible sidebar (docked/rail/drawer), content, not-found
- [x] `packages/shared` + `gen:api` script -- generated types from the OpenAPI schema
- [x] `src/api/client.ts` -- typed fetch wrapper, CSRF, `ApiError`
- [x] tests -- one per matrix row that runs in jsdom (shell landmarks, keyboard order, collapse persistence incl. storage failure, not-found, ApiError mapping, CSRF header, reduced-motion CSS present)
- [x] `docs/ARCHITECTURE_NOTES.md` -- web conventions note

**Acceptance Criteria:**
- Given a clean checkout, when `npm ci` then `npm run lint`, `npm run typecheck`, `npm run test`, `npm run build` run from the repo root, then all succeed.
- Given the dev servers running, when `/api/v1/health/` is requested through the Vite proxy, then it returns `{"status":"ok"}`.
- Given the shell at 1280, 820 and 390 px, when rendered in a real browser (Playwright screenshot or manual check recorded in notes), then layout matches the EXPERIENCE.md responsive rules and nothing overflows horizontally.

## Implementation Notes

- **TypeScript pinned to 5.9.3, not 7.0.2.** Registry peer ranges (checked 2026-10-29): `typescript-eslint@8.72.1` requires `typescript >=4.8.4 <6.1.0`; `openapi-typescript@7.13.0` requires `^5.x`. TypeScript 7 also no longer ships the classic JS compiler API those tools load. 5.9.3 is the newest version that satisfies every tool, so `npm ci` installs with no peer conflicts or overrides. Vite 8.3.5, Vitest 5.0.5 and `@vitejs/plugin-react` 6.1.2 put no constraint on TypeScript.
- **Pinned stack:** react/react-dom 19.3.1, react-router 8.5.1, vite 8.3.5, vitest 5.0.5, jsdom 30.1.3, eslint 10.13.0, typescript-eslint 8.72.1, openapi-typescript 7.13.0, @fontsource (source-serif-4 5.3.1, source-sans-3 5.3.1, jetbrains-mono 5.3.0). `.npmrc` sets `save-exact` and `engine-strict`. Node >= 22.22 because react-router 8 needs it.
- **Headless primitives (EXPERIENCE.md asked to confirm Radix at 1.1):** not adopted yet. The shell needs no dialog, menu or tabs; the sheet and drawer are a small in-house pattern (`inert` main, Escape closes, focus returns to the toggle). Decide when the first dialog lands (Story 1.6 or 1.7).
- **Navigation contents:** only "Home" exists. "New lesson", Library, Settings and the allowance indicator are left out until they have real behaviour (Never rule).
- **Backend schema fix (trivial, reported):** `core/views.py` health and ready had no response schema, so the generated type was untyped. Added `inline_serializer` responses (`Health`, `Ready`). The schema validates with `--fail-on-warn`; pytest still passes 105.
- **Schema gap found, not fixed:** `DELETE /api/v1/auth/account/` declares `requestBody?: never`, but the view expects a password body (Story 1.5). The generated type cannot express that request yet. Fix it in that view's `extend_schema(request=...)` when the deletion UI is built.
- **Real-browser check (2026-10-29, Edge headless via playwright-core, Vite dev server + Django):** at 1280 px the layout is `docked`: sidebar expanded, collapses to a 56 px rail, and the state survives a reload. At 820 px it is `rail`: icon rail, and the sheet opens over a scrim. At 390 px it is `drawer`: top bar with a menu button; the drawer opens under the top bar and focus moves to Home. Checked in light and dark at all three widths: no horizontal overflow (`scrollWidth <= clientWidth`), body background matches the `paper` token for each theme, self-hosted fonts load, no requests outside localhost, Tab order is skip link → toggle, the 2px focus ring is visible, and `/nope` shows the not-found page. With reduced motion, the computed transition duration is `0s`.
- **Proxy check:** `GET http://localhost:5173/api/v1/health/` returned `200 {"status":"ok"}`.

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `npm ci && npm run lint && npm run typecheck && npm run test && npm run build` -- expected: all pass
- `npm run gen:api` (API running) -- expected: no diff after regenerate
- `cd apps/api && .venv/Scripts/python -m pytest -q` -- expected: unchanged, 105 passed

## Orchestrator Review (2026-10-29)

- Re-ran independently from a deleted node_modules: `npm ci` (0 vulnerabilities), lint (0 warnings), typecheck, vitest 24 passed, build ok; backend pytest 105 passed, ruff clean, spectacular `--fail-on-warn` ok. No stray dev servers left running.
- Looked at the agent's screenshots (1280 light, 390 dark): matches DESIGN.md calm study-room look; no control without behaviour.
- TypeScript pinned to 5.9.3 (typescript-eslint 8.72.1 requires <6.1; openapi-typescript 7.13.0 requires 5.x); revisit when those support 6/7.
- Corrected agent's note on the account-deletion schema: the view does declare the request body, but drf-spectacular omits request bodies for DELETE, so the generated client lacks it (see deferred-work.md).
