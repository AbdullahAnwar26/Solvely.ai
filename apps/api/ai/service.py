"""AIService: timeouts, bounded retries and a concurrency cap around any `AIProvider` (AD-7).

- At most `AI_MAX_ATTEMPTS` provider calls per generation.
- Retryable errors are retried after exponential backoff with jitter; non-retryable errors
  (`provider_unavailable`) are raised at once.
- `provider_invalid_output` is retried at most `AI_MAX_INVALID_OUTPUT_RETRIES` times.
- Nothing runs past `AI_TOTAL_TIMEOUT_SECONDS`: each call gets
  min(`AI_CALL_TIMEOUT_SECONDS`, time left) as its timeout, and a backoff that would cross the
  deadline is not slept; the last typed error is raised instead.
- A process-wide BoundedSemaphore (`AI_MAX_CONCURRENCY`) bounds concurrent generations; if no
  slot frees up within `AI_CONCURRENCY_WAIT_SECONDS`, `provider_overloaded` is raised and the
  provider is not called.

Logs carry only the error code, model id, attempt, latency and request id (never prompts,
learner content, provider messages or keys).
"""
import logging
import random
import threading
import time

from django.conf import settings

from .errors import ProviderError, ProviderInvalidOutput, ProviderOverloaded, ProviderTimeout

logger = logging.getLogger(__name__)

_semaphore_lock = threading.Lock()
_semaphore = None
_semaphore_size = None


def process_semaphore():
    """The shared per-process semaphore, sized from settings when first used."""
    global _semaphore, _semaphore_size
    size = settings.AI_MAX_CONCURRENCY
    with _semaphore_lock:
        if _semaphore is None or _semaphore_size != size:
            _semaphore = threading.BoundedSemaphore(size)
            _semaphore_size = size
        return _semaphore


class AIService:
    def __init__(
        self,
        provider,
        *,
        sleep=time.sleep,
        clock=time.monotonic,
        jitter=random.random,
        semaphore=None,
        max_attempts=None,
        max_invalid_output_retries=None,
        call_timeout=None,
        total_timeout=None,
        concurrency_wait=None,
        backoff_base=None,
        backoff_max=None,
    ):
        self.provider = provider
        self._sleep = sleep
        self._clock = clock
        self._jitter = jitter
        self._semaphore = semaphore if semaphore is not None else process_semaphore()
        self.max_attempts = _pick(max_attempts, settings.AI_MAX_ATTEMPTS)
        self.max_invalid_output_retries = _pick(
            max_invalid_output_retries, settings.AI_MAX_INVALID_OUTPUT_RETRIES
        )
        self.call_timeout = _pick(call_timeout, settings.AI_CALL_TIMEOUT_SECONDS)
        self.total_timeout = _pick(total_timeout, settings.AI_TOTAL_TIMEOUT_SECONDS)
        self.concurrency_wait = _pick(concurrency_wait, settings.AI_CONCURRENCY_WAIT_SECONDS)
        self.backoff_base = _pick(backoff_base, settings.AI_BACKOFF_BASE_SECONDS)
        self.backoff_max = _pick(backoff_max, settings.AI_BACKOFF_MAX_SECONDS)

    def generate_json(self, request):
        if not self._semaphore.acquire(timeout=self.concurrency_wait):
            error = ProviderOverloaded(reason="concurrency_cap")
            self._log(error.code, 0, 0.0, request)
            raise error
        try:
            return self._run(request)
        finally:
            self._semaphore.release()

    def _run(self, request):
        deadline = self._clock() + self.total_timeout
        invalid_retries = 0
        last_error = None
        for attempt in range(1, self.max_attempts + 1):
            remaining = deadline - self._clock()
            if remaining <= 0:
                break
            attempt_request = request.model_copy(
                update={"timeout_seconds": min(self.call_timeout, remaining)}
            )
            started = self._clock()
            try:
                result = self.provider.generate_json(attempt_request)
            except ProviderError as error:
                self._log(error.code, attempt, self._clock() - started, request)
                last_error = error
                if not error.retryable or attempt >= self.max_attempts:
                    raise
                if isinstance(error, ProviderInvalidOutput):
                    if invalid_retries >= self.max_invalid_output_retries:
                        raise
                    invalid_retries += 1
                delay = self._backoff(attempt)
                if self._clock() + delay >= deadline:
                    raise
                self._sleep(delay)
                continue
            self._log("ok", attempt, self._clock() - started, request, model=result.model)
            return result
        # The deadline passed before another attempt could start.
        raise last_error if last_error is not None else ProviderTimeout(reason="deadline")

    def _backoff(self, attempt):
        ceiling = min(self.backoff_max, self.backoff_base * 2 ** (attempt - 1))
        # "Equal jitter": half fixed, half random, so retries spread out but never collapse to 0.
        return ceiling / 2 + self._jitter() * ceiling / 2

    def _log(self, code, attempt, latency, request, model=None):
        logger.info(
            "ai_call code=%s provider=%s model=%s attempt=%d latency_ms=%d request_id=%s",
            code,
            getattr(self.provider, "name", None),
            model or getattr(self.provider, "model", None),
            attempt,
            round(latency * 1000),
            request.request_id,
        )


def _pick(value, default):
    return default if value is None else value
