# Architecture Notes

## Adding an owned model and endpoint (AD-5)

1. Subclass `core.ownership.OwnedModel` (gives `owner`, `created_at`, `updated_at`). Keep its default manager: `objects` must stay an `OwnedManager`.
2. Never put `owner` in a serializer's writable fields; the owner is always `request.user`.
3. Serve it with `core.viewsets.OwnedModelViewSet`, setting `model = YourModel` (not `queryset`). It requires authentication, scopes every query through `for_user(request.user)`, returns the 404 `not_found` envelope for foreign or missing ids, and sets the owner on create/update.
4. In any other code path, fetch rows only via `YourModel.objects.for_user(user)`.
5. Register the endpoint in `apps/api/tests/isolation.py` with `register_owned_endpoint(model, url, make=..., create_payload=..., update_payload=...)`. The shared cross-user checks in `tests/test_ownership.py` then run against it; an unregistered concrete `OwnedModel` fails the guard test.
6. Account deletion (Story 1.5) relies on `on_delete=CASCADE` from `owner`; keep it.

Owned models are deleted by cascade when their user is deleted; any new FK to the user model must use `on_delete=CASCADE` (enforced by the FK guard in `tests/test_account_deletion.py`).

## Web app conventions (apps/web, packages/shared)

- **Workspace:** npm workspaces from the repo root (`apps/web`, `packages/shared`), Node >= 22.22. Versions are pinned exactly (`.npmrc` has `save-exact=true`); commit `package-lock.json`.
- **Commands (repo root):** `npm ci`, then `npm run lint`, `npm run typecheck`, `npm run test` (Vitest + Testing Library, jsdom), `npm run build`. `npm run dev` starts Vite on http://localhost:5173 and proxies `/api` to http://localhost:8000 (override with `API_URL`), so session and CSRF cookies stay same-origin.
- **TypeScript:** pinned to 5.9.3, `strict`. TypeScript 7 (and 6) are not yet supported by `typescript-eslint` (peer `<6.1.0`) or `openapi-typescript` (peer `^5.x`); revisit when both widen their ranges.
- **Tokens:** `apps/web/src/styles/tokens.css` mirrors DESIGN.md: `--color-*` (light and dark sets), `--font-*`, `--space-*`, `--radius-*`, `--motion-*`, `--elevation-*`. The dark set applies under `prefers-color-scheme: dark` unless `<html data-theme="light">`, and always under `data-theme="dark"`. Components use variables only; ESLint rejects hex colour literals in TS/TSX. Add any new colour to both sets.
- **Fonts:** self-hosted via `@fontsource` (imported in `src/styles/fonts.ts`), bundled by Vite with `font-display: swap`; no runtime third-party requests.
- **Shell:** `src/app/AppShell.tsx`. Layout mode follows EXPERIENCE.md breakpoints (`src/app/layoutMode.ts`): `docked` >= 1200px (collapsible, remembered in `localStorage` under `wt.sidebar.collapsed`), `rail` 768-1199px (icon rail, sheet on demand), `drawer` < 768px (top bar + drawer). Route components are `React.lazy` pages in `src/app/routes.tsx`. Base styles give every focusable a 2px `--color-focus` ring and drop all transitions/animations under `prefers-reduced-motion: reduce`.
- **API calls:** only through `src/api/client.ts` (`api.get("/api/v1/health/")` etc.). Paths, request bodies and responses are typed from `@solvely/shared`. It sends `credentials: "include"`, copies the `csrftoken` cookie into `X-CSRFToken` on POST/PUT/PATCH/DELETE, and throws `ApiError` (`status`, `code`, `message`, `retryable`, `request_id`, `fields`) for any non-2xx; a body without the error envelope becomes `code: "http_error"`, a network failure `code: "network_error"`. Aborts are re-thrown unchanged.
- **Regenerating API types:** start the API (`cd apps/api && .venv/Scripts/python manage.py runserver`), then `npm run gen:api` from the root. It fetches `GET /api/v1/schema/` (override the origin with `API_URL`) and rewrites `packages/shared/src/generated/api.ts`; commit the result. Output is deterministic, so a clean re-run must leave no diff. If an endpoint's response shows up as `undefined`/`never`, its drf-spectacular schema is missing a response serializer: fix it in the view.
