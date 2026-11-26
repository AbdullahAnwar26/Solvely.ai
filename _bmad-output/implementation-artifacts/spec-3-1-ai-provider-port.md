---
title: 'Story 3.1: AI provider port, Gemini adapter and FakeProvider'
type: 'feature'
created: '2026-10-29'
status: 'done'
baseline_commit: '33593b4'
route: 'dispatch'
review_loop_iteration: 0
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture/architecture-Solvely.ai-2026-10-27/ARCHITECTURE-SPINE.md'
  - '{project-root}/_bmad-output/planning-artifacts/epics.md'
  - '{project-root}/_bmad-output/planning-artifacts/prds/prd-Solvely.ai-2026-10-27/prd.md'
  - '{project-root}/_bmad-output/planning-artifacts/briefs/brief-Solvely.ai-2026-10-27/addendum.md'
  - '{project-root}/docs/ARCHITECTURE_NOTES.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Epic 3 needs to call an AI model for lessons, but there is no provider boundary. Without one, teaching logic would couple to the Gemini SDK (AD-1), tests could hit the paid API (AD-12), failures could look like success (AD-11), and nothing bounds timeouts, retries or concurrency.

**Approach:** Add an `ai` Django app with a provider port (framework-free types), a Gemini adapter that is the only importer of `google.genai`, a deterministic `FakeProvider` for all automated tests, a small service that applies timeout, bounded retries and a concurrency limit, typed errors that map to the API error envelope, and an admin-only diagnostic that never reveals credentials.

## Boundaries & Constraints

**Always:** App `apps/api/ai/`. Port in `ai/ports.py`: an `AIProvider` protocol with one method `generate_json(request) -> ProviderResult`; `ProviderRequest` carries `system_instruction: str` (trusted, from versioned prompts only), `user_content: str` (untrusted learner or model-derived text; the adapter MUST pass it only as user content, never concatenated into the system instruction; AD-9), `response_schema: dict` (JSON schema), `request_id`, `max_output_tokens`; `ProviderResult` carries `data: dict | list` (already `json.loads`-ed, but NOT yet domain-validated), `usage` (`input_tokens`, `output_tokens`, may be None), `model`. These port types use only stdlib and pydantic (no Django, no SDK imports). Typed errors in `ai/errors.py`, each with a stable code and `retryable`: `provider_unavailable` (not configured, auth failure, model not found; not retryable), `provider_timeout` (retryable), `provider_rate_limited` (retryable), `provider_error` (5xx or network; retryable), `provider_invalid_output` (empty, non-JSON, blocked or truncated; retryable once), `provider_overloaded` (our own concurrency cap exceeded, retryable). They are API errors (reuse the `ApiError` base in `core/errors.py`) mapped to HTTP 503 (unavailable, rate limited, overloaded), 504 (timeout), 502 (provider_error, invalid output), with the standard envelope; no provider message text, key, prompt or stack trace in responses; log only code, model id, attempt, latency and `request_id` at INFO. `ai/providers/gemini.py` is the ONLY file importing `google.genai`; it uses the official `google-genai` SDK (version pinned in requirements; check the installed package and the current official docs at https://ai.google.dev for the structured-output and timeout APIs instead of guessing), reads `GEMINI_API_KEY` and `GEMINI_MODEL` from settings (environment), and requests JSON output constrained by `response_schema`; maps SDK exceptions and finish reasons (safety block, max tokens, empty) to the typed errors; reports token usage when the SDK returns it; sets an explicit HTTP timeout. Do NOT hard-code a default model id anywhere: if `GEMINI_MODEL` or the key is missing, calls raise `provider_unavailable`. In `.env.example` document `GEMINI_MODEL` with a comment naming a Flash-class model you verified in the official docs today plus the verification date, and note that availability, quotas, rate limits and pricing are controlled by Google and must be checked before deployment. `ai/service.py`: `AIService(provider)` with `generate_json(request)` applying (settings, named constants in `core/limits.py` or `ai/limits.py`): total attempts at most 3 (`AI_MAX_ATTEMPTS`), exponential backoff with jitter only for retryable errors and never past an overall deadline (`AI_TOTAL_TIMEOUT_SECONDS`), a per-call provider timeout (`AI_CALL_TIMEOUT_SECONDS`), and a process-wide `BoundedSemaphore` (`AI_MAX_CONCURRENCY`, acquired with a short wait; failing to acquire raises `provider_overloaded` without calling the provider). `provider_invalid_output` is retried at most once. Non-retryable errors are never retried. Sleep and clock are injectable so tests run instantly. `ai/providers/fake.py` `FakeProvider`: scripted responses and failures in order (valid, malformed JSON, oversized, repeated, partial, truncated, empty, plus injected errors of every typed kind and artificial delay), records every request it received, can assert it never sees secrets, and raises a clear error if its script is exhausted. A provider factory `get_provider()` reads `AI_PROVIDER` (default `gemini`; the test settings set `fake`) so views and services never name a vendor. Diagnostics: `GET /api/v1/ai/status/` restricted to staff (`IsAdminUser`), returns `{configured: bool, provider: "gemini"|"fake", model: str|null, max_attempts, max_concurrency}` and NEVER the key or any part of it; 403 for non-staff, 403 for anonymous; with `extend_schema`; spectacular must pass `--fail-on-warn`; regenerate `packages/shared` types. Tests: all automated tests use `FakeProvider` or mock at the `AIProvider` boundary; add a conftest guard that makes constructing a real `google.genai` client fail the test unless the test is marked `live`; add a guard test that scans the source tree and fails if any file other than `ai/providers/gemini.py` imports `google.genai`, and that no model-id string literal such as `gemini-` appears in application code outside tests and `.env.example`; mark an optional live smoke test with `@pytest.mark.live` that is skipped unless `GEMINI_API_KEY` and `GEMINI_MODEL` are set AND `-m live` is passed, register the marker in `pyproject.toml`, and exclude `live` by default. Dependencies: use already-pinned `google-genai` and `pydantic`; add none.

**Never:** No lesson prompts, schemas or Board Operation validation (Stories 3.2 and 3.5), no endpoint that calls the model for learners, no streaming, no usage charging or allowance (Story 3.4), no secrets in logs, responses, tests or committed files, no real network call in any default test run, no anthropic or other vendor code, no change to Epic 1 or 2 behaviour.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | FakeProvider valid JSON | `ProviderResult` with data, usage, model | N/A |
| Not configured | no key or no model (gemini provider) | `provider_unavailable`, not retried, no SDK network call | envelope 503 |
| Timeout | provider raises timeout twice then succeeds | retried with backoff within deadline, returns result | final failure -> `provider_timeout` 504 |
| Rate limited | 429 then success | retried, result returned | exhausted -> `provider_rate_limited` 503 |
| Provider 5xx or network | error then success | retried | exhausted -> `provider_error` 502 |
| Auth or model-not-found | provider unavailable error | not retried, `provider_unavailable` | 503 |
| Malformed JSON | non-JSON text | retried once; second malformed -> `provider_invalid_output` | 502 |
| Empty or blocked or truncated | no candidates, safety block, max tokens | `provider_invalid_output` | 502 |
| Concurrency cap | more concurrent calls than `AI_MAX_CONCURRENCY` | extra call fails fast with `provider_overloaded`, provider not called | 503 retryable |
| Overall deadline | retries would pass `AI_TOTAL_TIMEOUT_SECONDS` | stops retrying, raises last typed error | N/A |
| Prompt separation | untrusted text with fake instructions | passed only as user content; system instruction unchanged | N/A |
| Secret hygiene | any path | key never appears in logs, errors, `repr`, diagnostics | N/A |
| Diagnostics staff | staff user | 200 with configured flag, model, limits, no key | N/A |
| Diagnostics other | anonymous or normal user | 403 | envelope |
| Import guard | source scan | only `gemini.py` imports `google.genai`; no `gemini-` literal in app code | test fails otherwise |
| Network guard | default test run | constructing a real client fails the test | N/A |
| Live test | no key or no `-m live` | skipped | N/A |

</frozen-after-approval>

## Code Map

- `apps/api/ai/` -- new app: `ports.py`, `errors.py`, `service.py`, `factory.py`, `providers/gemini.py`, `providers/fake.py`, `views.py` (diagnostics), `urls.py`, `apps.py`; register in `config/settings.py` (INSTALLED_APPS, env settings with safe defaults) and `config/urls.py`.
- `apps/api/core/errors.py` -- reuse `ApiError`; do not weaken the envelope.
- `apps/api/core/limits.py` -- named AI limits.
- `apps/api/config/settings_test.py` -- `AI_PROVIDER = "fake"`; tiny timeouts and no sleeping.
- `apps/api/tests/` -- `test_ai_service.py`, `test_ai_gemini_adapter.py` (SDK mocked at the `google.genai` client boundary, only inside this test), `test_ai_guards.py`, `test_ai_status.py`; `conftest.py` network guard; `pyproject.toml` marker.
- `apps/api/.env.example` -- document variables.
- `packages/shared/src/generated/api.ts` -- regenerate with `npm run gen:api` (API running).
- `docs/ARCHITECTURE_NOTES.md` -- short "AI provider boundary" section (how to add a provider, how tests stay offline, error codes).

## Tasks & Acceptance

**Execution:**
- [x] port types, typed errors and envelope mapping
- [x] `AIService` with injectable clock and sleep, bounded retries, deadline, semaphore
- [x] `FakeProvider` with scripted fixtures and failure injection
- [x] Gemini adapter (only SDK importer), verified against the installed SDK and current official docs; no hard-coded model
- [x] factory, settings, diagnostics endpoint, schema, regenerated types
- [x] tests: one per matrix row; mutation check (temporarily allow the system instruction to include user text, or remove the semaphore, or remove the retry cap, and confirm tests fail; then restore)
- [x] guard tests (import scan, model literal scan, network guard), `live` marker and optional live smoke test (do not run it; no key is available)
- [x] docs note and `.env.example`

**Acceptance Criteria:**
- Given any default test run, when it executes, then no network call is made and no real `google.genai` client is constructed.
- Given transient provider failures, when the service runs, then retries are bounded by attempts and an overall deadline and the final error is typed with the right HTTP status; non-retryable errors are not retried.
- Given the source tree, when scanned, then only `ai/providers/gemini.py` imports `google.genai` and no model id literal exists in application code.
- Given a non-staff user, when they call the diagnostics endpoint, then they get 403, and no response or log ever contains the API key.
- Given a clean checkout, when `pytest`, `ruff check`, `makemigrations --check`, `spectacular --validate --fail-on-warn` and root `npm run lint`, `typecheck`, `test`, `build` run, then all pass.

## Implementation Notes

- `ProviderRequest` has one field beyond the listed ones: optional `timeout_seconds`, which `AIService` sets per attempt to min(`AI_CALL_TIMEOUT_SECONDS`, time left before the deadline); the Gemini adapter passes it as the per-call `HttpOptions.timeout`.
- SDK API: the official text-generation and structured-output guides now show the newer `client.interactions.create` API; this adapter uses `client.models.generate_content` (still documented at https://ai.google.dev/api/generate-content, not deprecated, and typed in the installed SDK 2.33.0 with finish reasons and usage metadata), with `response_json_schema` + `response_mime_type="application/json"`. SDK retries (`HttpRetryOptions(attempts=1)`) and `automatic_continuation` are off so only `AIService` retries.
- Error mapping by HTTP status only: 429 rate limited; 408 timeout; 5xx provider_error; 401/403 auth, 404 model not found, and any other 4xx (including 400, which Gemini uses for invalid keys and refused schemas) -> `provider_unavailable` (not retryable). `httpx` timeouts -> timeout; other `httpx`/`OSError` -> provider_error; unknown exceptions -> provider_error. Exceptions are re-raised `from None` so SDK text never reaches logs.
- Model verified for `.env.example`: `gemini-3.8-flash` (stable Flash-class, models page dated 2026-10-28, checked 2026-10-29).
- Unexpected (non-provider) exceptions are not caught by `AIService`; the FakeProvider's `FakeScriptExhausted` therefore stays loud in tests.
- Mutation checks run and restored: user text in system instruction (adapter test fails), semaphore bypass (fails), retry cap removed (loop bound and in-loop cap; 8 fail), non-retryable retried (fails), invalid-output budget removed (fails), deadline check removed (fails). Removing only the loop bound survives because the in-loop cap is a second guard.

## Spec Change Log

## Review Triage Log

## Verification

**Commands:**
- `cd apps/api && .venv/Scripts/python -m pytest -q && .venv/Scripts/python -m ruff check . && .venv/Scripts/python manage.py makemigrations --check` -- expected: pass, no changes
- `DJANGO_SETTINGS_MODULE=config.settings DJANGO_SECRET_KEY=x .venv/Scripts/python manage.py spectacular --validate --fail-on-warn --file /dev/null` -- expected: exit 0
- `npm run lint && npm run typecheck && npm run test && npm run build` (repo root) -- expected: all pass

## Orchestrator Review (2026-10-29)

- Re-ran independently: backend pytest 305 passed (1 live test deselected), ruff clean, `makemigrations --check` clean, spectacular `--fail-on-warn` exit 0; web lint 0 warnings, typecheck, vitest 172 passed, build ok. Ports free.
- Scans: only `ai/providers/gemini.py` imports `google.genai` at runtime (tests import it only for guards and the adapter test); the only key-like strings are labelled fake fixtures in tests; no real key anywhere.
- Read `AIService`: semaphore acquired first and released in `finally`; per-attempt timeout is min(call timeout, time left); non-retryable errors raise immediately; invalid output retried at most once; backoff with equal jitter stops at the overall deadline; sleep/clock injectable. Mutation checks reported by the agent (system instruction polluted, semaphore bypassed, retry cap removed, non-retryable retried, invalid-output budget removed, deadline removed) accepted.
- NOT verified: the Gemini adapter has never made a real call (no key); it is checked only against the installed SDK 2.33.0 types and mocks. It uses `client.models.generate_content` with `response_json_schema` and JSON MIME type; the official guides now also show an `interactions` API, so re-check docs at the first live call. `gemini-3.8-flash` in `.env.example` comes from the agent's reading of the official models page dated 2026-10-28.
- Accepted choices: any 4xx other than 408 and 429 maps to `provider_unavailable` (not retried), including 400 for refused schemas; `output_tokens` includes thinking tokens; running `-m live` with a real `.env` makes a real (billed) call only on explicit opt-in.
