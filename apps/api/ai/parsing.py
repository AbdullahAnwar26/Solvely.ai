"""Turn raw model text into JSON data, shared by every provider adapter."""
import json

from .errors import ProviderInvalidOutput


def _reject_constant(value):
    # NaN, Infinity and -Infinity are not JSON.
    raise ValueError(value)


def parse_json_output(text):
    """Return the decoded object or array; raise `provider_invalid_output` otherwise.

    Only JSON syntax is checked here. Domain validation (Story 3.2) happens later.
    """
    if text is None or not text.strip():
        raise ProviderInvalidOutput(reason="empty")
    try:
        data = json.loads(text, parse_constant=_reject_constant)
    except (ValueError, RecursionError):
        raise ProviderInvalidOutput(reason="non_json") from None
    if not isinstance(data, dict | list):
        raise ProviderInvalidOutput(reason="not_object_or_array")
    return data
