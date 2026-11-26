"""Optional live smoke test against the real Gemini API.

Never part of a default run: `pyproject.toml` deselects the `live` marker, and the test also
skips unless `-m live` was passed AND GEMINI_API_KEY and GEMINI_MODEL are set. It makes one
small paid call. Run it only on purpose:

    .venv/Scripts/python -m pytest -m live tests/test_ai_live.py
"""
import threading

import pytest
from django.conf import settings

from ai.ports import ProviderRequest
from ai.providers.gemini import GeminiProvider
from ai.service import AIService


@pytest.mark.live
def test_gemini_returns_schema_shaped_json(request):
    if "live" not in (request.config.getoption("-m") or "") or "not live" in (
        request.config.getoption("-m") or ""
    ):
        pytest.skip("live tests need `-m live`")
    if not (settings.GEMINI_API_KEY and settings.GEMINI_MODEL):
        pytest.skip("GEMINI_API_KEY and GEMINI_MODEL are not set")

    # The test settings use tiny AI timeouts for the offline tests; a real call needs real ones.
    service = AIService(
        GeminiProvider.from_settings(),
        semaphore=threading.BoundedSemaphore(1),
        call_timeout=60,
        total_timeout=150,
        max_attempts=3,
        backoff_base=2,
        backoff_max=10,
    )
    result = service.generate_json(
        ProviderRequest(
            system_instruction="Answer the arithmetic question as JSON.",
            user_content="What is 2 + 3?",
            response_schema={
                "type": "object",
                "properties": {"answer": {"type": "integer"}},
                "required": ["answer"],
            },
            request_id="live-smoke",
            # Room for thinking tokens, which count towards the output limit.
            max_output_tokens=2048,
        )
    )
    assert result.data == {"answer": 5}
    assert result.model
