"""Gemini adapter: the ONLY module that imports `google.genai` (AD-1).

Built against google-genai 2.33.0 (`requirements.txt`) and checked against the installed SDK and
https://ai.google.dev/api/generate-content on 2026-10-29:

- `client.models.generate_content(model=..., contents=..., config=GenerateContentConfig(...))`.
- Structured output: `response_mime_type="application/json"` plus `response_json_schema` (a plain
  JSON Schema dict; the SDK requires the mime type when this is set).
- Timeout: `HttpOptions.timeout` is in milliseconds; it is set on the client and per call.
- Retries: the SDK's own retry is switched off (`HttpRetryOptions(attempts=1)`), and so is
  `automatic_continuation`; AIService alone decides about retries.
- Errors: `google.genai.errors.APIError` (`ClientError` 4xx, `ServerError` 5xx) carry `.code`;
  timeouts and connection failures surface as `httpx` exceptions.

The key is read from settings and lives only on the SDK client; it is never logged, put in an
error or shown by `repr`. No model id is hard-coded: without `GEMINI_MODEL` or
`GEMINI_API_KEY` every call raises `provider_unavailable` without touching the network.
"""
import logging

import httpx
from django.conf import settings
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from ..errors import (
    ProviderFailure,
    ProviderInvalidOutput,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)
from ..parsing import parse_json_output
from ..ports import ProviderResult, Usage

logger = logging.getLogger(__name__)

# Finish reasons that mean the model completed normally.
_OK_FINISH_REASONS = {None, "STOP", "FINISH_REASON_UNSPECIFIED"}


def _enum_name(value):
    if value is None:
        return None
    return str(getattr(value, "value", value)).upper()


def map_api_error(exc):
    """Map an SDK APIError to a typed error by HTTP status only (never by message text)."""
    code = getattr(exc, "code", None)
    if code == 429:
        return ProviderRateLimited(reason="http_429")
    if code == 408:
        return ProviderTimeout(reason="http_408")
    if isinstance(code, int) and code >= 500:
        return ProviderFailure(reason=f"http_{code}")
    if code in (401, 403):
        return ProviderUnavailable(reason="auth")
    if code == 404:
        return ProviderUnavailable(reason="model_not_found")
    if isinstance(code, int) and 400 <= code < 500:
        # 400 covers an invalid key as well as a request the API refuses (for example a schema
        # it cannot handle); retrying cannot fix either.
        return ProviderUnavailable(reason=f"http_{code}")
    return ProviderFailure(reason="api_error")


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key, model, *, timeout_seconds, client_factory=None):
        self._api_key = api_key or ""
        self.model = model or None
        self._timeout_seconds = timeout_seconds
        self._client_factory = client_factory or genai.Client
        self._client = None

    @classmethod
    def from_settings(cls):
        return cls(
            settings.GEMINI_API_KEY,
            settings.GEMINI_MODEL,
            timeout_seconds=settings.AI_CALL_TIMEOUT_SECONDS,
        )

    @property
    def configured(self):
        return bool(self._api_key and self.model)

    def __repr__(self):
        return f"GeminiProvider(model={self.model!r}, configured={self.configured})"

    def _http_options(self, timeout_seconds):
        return types.HttpOptions(
            timeout=max(1, int(timeout_seconds * 1000)),
            retry_options=types.HttpRetryOptions(attempts=1),
        )

    def _get_client(self):
        if not self.configured:
            raise ProviderUnavailable(reason="not_configured")
        if self._client is None:
            try:
                self._client = self._client_factory(
                    api_key=self._api_key, http_options=self._http_options(self._timeout_seconds)
                )
            except Exception:
                logger.warning("ai_client_init_failed provider=gemini model=%s", self.model)
                raise ProviderUnavailable(reason="client_init") from None
        return self._client

    def generate_json(self, request):
        client = self._get_client()
        timeout = request.timeout_seconds or self._timeout_seconds
        config = types.GenerateContentConfig(
            # Trusted, versioned prompt text only (AD-9).
            system_instruction=request.system_instruction,
            response_mime_type="application/json",
            response_json_schema=request.response_schema,
            max_output_tokens=request.max_output_tokens,
            candidate_count=1,
            automatic_continuation=False,
            http_options=self._http_options(timeout),
        )
        # Untrusted text goes only into the user turn, never into the system instruction.
        contents = [types.Content(role="user", parts=[types.Part(text=request.user_content)])]
        try:
            response = client.models.generate_content(
                model=self.model, contents=contents, config=config
            )
        except genai_errors.APIError as exc:
            raise map_api_error(exc) from None
        except httpx.TimeoutException:
            raise ProviderTimeout(reason="http_timeout") from None
        except (httpx.HTTPError, OSError):
            raise ProviderFailure(reason="network") from None
        except Exception:
            # Unknown SDK failure: keep its text out of logs and responses.
            raise ProviderFailure(reason="sdk_error") from None
        return self._to_result(response)

    def _to_result(self, response):
        feedback = getattr(response, "prompt_feedback", None)
        if feedback is not None and getattr(feedback, "block_reason", None):
            raise ProviderInvalidOutput(reason="prompt_blocked")
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            raise ProviderInvalidOutput(reason="empty")
        candidate = candidates[0]
        finish = _enum_name(getattr(candidate, "finish_reason", None))
        if finish == "MAX_TOKENS":
            raise ProviderInvalidOutput(reason="truncated")
        if finish not in _OK_FINISH_REASONS:
            raise ProviderInvalidOutput(reason=f"finish_{finish.lower()}")
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        text = "".join(
            part.text
            for part in parts
            if isinstance(getattr(part, "text", None), str) and not getattr(part, "thought", None)
        )
        data = parse_json_output(text)
        return ProviderResult(
            data=data,
            usage=_usage(getattr(response, "usage_metadata", None)),
            model=getattr(response, "model_version", None) or self.model,
        )


def _usage(metadata):
    if metadata is None:
        return Usage()
    prompt = getattr(metadata, "prompt_token_count", None)
    candidates = getattr(metadata, "candidates_token_count", None)
    thoughts = getattr(metadata, "thoughts_token_count", None)
    # Thinking tokens are billed as output, so they count towards output_tokens.
    output = None
    if candidates is not None or thoughts is not None:
        output = (candidates or 0) + (thoughts or 0)
    return Usage(input_tokens=prompt, output_tokens=output)
