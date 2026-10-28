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
