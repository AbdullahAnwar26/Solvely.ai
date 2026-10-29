- source_spec: none
  summary: Story 1.3 sign in, sign out, password reset (backend)
  evidence: split from the Epic 1 backend batch by the multi-goal check; build next, after 1.2.
- source_spec: none
  summary: Story 1.4 owner-scoped data foundation (OwnedModel, for_user manager, cross-user test harness)
  evidence: split from the Epic 1 backend batch by the multi-goal check.
- source_spec: none
  summary: Story 1.5 account deletion
  evidence: split from the Epic 1 backend batch by the multi-goal check; depends on 1.2 users and 1.4 ownership.
- source_spec: `_bmad-output/implementation-artifacts/spec-1-4-owner-scoped-data-foundation.md`
  summary: Fix drf-spectacular schema errors (9) on accounts auth views and health/ready so the OpenAPI contract is clean before the web client is generated
  evidence: `spectacular --validate --fail-on-warn` fails under test settings; pre-existing from stories 1.2/1.3. Do this at the start of Story 1.1.
- RESOLVED 2026-10-28: drf-spectacular errors fixed with @extend_schema on account and health/ready views; `spectacular --validate --fail-on-warn` passes.
- source_spec: `_bmad-output/planning-artifacts/ux-designs/ux-Solvely.ai-2026-10-28/EXPERIENCE.md`
  summary: Lesson schema (Story 3.2) needs a per-Step text description and a completion field for the "I've got it" moment (UJ-2); confirm Excalidraw origin badges in Story 2.2
  evidence: gaps listed by the UX distill step.
- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-web-app-shell-and-api-client.md`
  summary: Decide how the web client sends the account-deletion password: drf-spectacular emits no request body for DELETE, and some proxies drop DELETE bodies. Options: move to `POST /api/v1/auth/account/delete/` (recommended, robust, typed) or keep DELETE and hand-type the body. Decide in Story 1.6 (account settings UI).
  evidence: generated `auth_account_destroy` has `requestBody?: never` although the view declares AccountDeleteSerializer.
- source_spec: `_bmad-output/implementation-artifacts/spec-1-1-web-app-shell-and-api-client.md`
  summary: Choose and add the accessible dialog/menu primitive (Radix UI was assumed) at the first dialog (Story 1.6 or 1.7); main bundle is 319 kB (101 kB gzip), mostly React Router 8.
  evidence: shell has no dialogs yet; drawer uses its own focus handling.
- source_spec: `_bmad-output/implementation-artifacts/spec-1-6-theme-and-account-settings.md`
  summary: Add a request timeout (AbortController) and a visible retry state to the web API client so a stalled request cannot leave a form stuck on a busy state forever
  evidence: `apps/web/src/api/client.ts` has no timeout; a live run once hung on "Signing in…" (cause unproven, likely a test-script artifact).
