"""Typed provider errors (AD-11). Each maps to the standard API error envelope.

Messages are fixed, user-safe strings: provider message text, keys, prompts and stack traces
never reach a response. `reason` is a short internal tag (for example `finish_max_tokens`) used
only in server logs; it is always one of our own constants, never SDK text.
"""
from core.errors import ApiError


class ProviderError(ApiError):
    """Base class: code, HTTP status and `retryable` are fixed per subclass."""

    status_code = 502
    default_code = "provider_error"
    default_detail = "The tutor could not answer right now. Please try again."
    retryable = True

    def __init__(self, reason=None):
        # Always the fixed message; never pass provider text through.
        super().__init__()
        self.reason = reason

    @property
    def code(self):
        return self.default_code

    def __repr__(self):
        return f"{type(self).__name__}(code={self.code!r}, reason={self.reason!r})"


class ProviderUnavailable(ProviderError):
    """Not configured, authentication failed, model not found or request refused (4xx)."""

    status_code = 503
    default_code = "provider_unavailable"
    default_detail = "The tutor is not available right now."
    retryable = False


class ProviderTimeout(ProviderError):
    status_code = 504
    default_code = "provider_timeout"
    default_detail = "The tutor took too long to answer. Please try again."
    retryable = True


class ProviderRateLimited(ProviderError):
    status_code = 503
    default_code = "provider_rate_limited"
    default_detail = "The tutor is busy right now. Please try again in a moment."
    retryable = True


class ProviderFailure(ProviderError):
    """Provider 5xx or network failure (`provider_error`)."""

    status_code = 502
    default_code = "provider_error"
    default_detail = "The tutor could not answer right now. Please try again."
    retryable = True


class ProviderInvalidOutput(ProviderError):
    """Empty, non-JSON, blocked or truncated output. AIService retries it at most once."""

    status_code = 502
    default_code = "provider_invalid_output"
    default_detail = "The tutor gave an answer we could not use. Please try again."
    retryable = True


class ProviderOverloaded(ProviderError):
    """Our own concurrency cap is full; the provider was not called."""

    status_code = 503
    default_code = "provider_overloaded"
    default_detail = "Too many lessons are being prepared right now. Please try again shortly."
    retryable = True


ALL_PROVIDER_ERRORS = (
    ProviderUnavailable,
    ProviderTimeout,
    ProviderRateLimited,
    ProviderFailure,
    ProviderInvalidOutput,
    ProviderOverloaded,
)
