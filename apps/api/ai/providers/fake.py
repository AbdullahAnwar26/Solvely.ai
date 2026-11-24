"""FakeProvider: a deterministic, scripted `AIProvider` for every automated test (AD-12).

Script it with steps, served in order, one per call:

    fake = FakeProvider([fake_error("provider_timeout"), valid({"steps": []})])

Each step is a `FakeReply` (raw model text, parsed like a real provider would) or a
`FakeFailure` (raises a typed error). Any step can carry an artificial `delay`; a delay longer
than the call's timeout raises `provider_timeout`, as a real HTTP timeout would. When the
script runs out, `FakeScriptExhausted` is raised: a test that makes more calls than it
scripted fails loudly instead of getting an invented answer.
"""
import json
import time
from dataclasses import dataclass, field

from ..errors import (
    ProviderFailure,
    ProviderInvalidOutput,
    ProviderOverloaded,
    ProviderRateLimited,
    ProviderTimeout,
    ProviderUnavailable,
)
from ..parsing import parse_json_output
from ..ports import ProviderResult, Usage

FAKE_MODEL = "fake-model"

ERRORS_BY_CODE = {
    cls.default_code: cls
    for cls in (
        ProviderUnavailable,
        ProviderTimeout,
        ProviderRateLimited,
        ProviderFailure,
        ProviderInvalidOutput,
        ProviderOverloaded,
    )
}


class FakeScriptExhausted(AssertionError):
    """The FakeProvider was called more often than its script allows."""


@dataclass(frozen=True)
class FakeReply:
    text: str
    usage: Usage = field(default_factory=lambda: Usage(input_tokens=10, output_tokens=20))
    delay: float = 0.0
    # Simulates a provider-side stop reason that makes the output unusable ("truncated",
    # "blocked"); None means the model finished normally.
    stop_problem: str | None = None


@dataclass(frozen=True)
class FakeFailure:
    code: str
    delay: float = 0.0


# --- Fixtures -----------------------------------------------------------------------------


def valid(data, **kwargs):
    """Well-formed JSON output."""
    return FakeReply(json.dumps(data), **kwargs)


def malformed(**kwargs):
    """Text that is not JSON at all."""
    return FakeReply("Sure! Here is your lesson: {steps: [oops", **kwargs)


def oversized(items=5000, text_length=2000, **kwargs):
    """Valid JSON far beyond any sane lesson size (for Story 3.2 limit checks)."""
    data = {"steps": [{"title": f"Step {i}", "text": "x" * text_length} for i in range(items)]}
    return valid(data, **kwargs)


def repeated(item=None, times=50, **kwargs):
    """Valid JSON that repeats the same item over and over."""
    item = item if item is not None else {"type": "add_element", "id": "same", "text": "again"}
    return valid({"operations": [item] * times}, **kwargs)


def partial(**kwargs):
    """Valid JSON with required parts missing (structurally incomplete for the domain)."""
    return valid({"steps": [{"title": "Only a title"}]}, **kwargs)


def truncated(**kwargs):
    """Output cut off at the output-token limit: incomplete JSON and a max-tokens stop."""
    return FakeReply('{"steps": [{"title": "Step 1", "text": "The deriv', stop_problem="truncated",
                     **kwargs)


def blocked(**kwargs):
    """A safety block: no usable text."""
    return FakeReply("", stop_problem="blocked", **kwargs)


def empty(**kwargs):
    """An empty answer (no candidates or no text)."""
    return FakeReply("", **kwargs)


def fake_error(code, **kwargs):
    """Inject a typed error by its stable code, for example `provider_rate_limited`."""
    if code not in ERRORS_BY_CODE:
        raise ValueError(f"Unknown provider error code: {code}")
    return FakeFailure(code, **kwargs)


# --- Provider -----------------------------------------------------------------------------


class FakeProvider:
    name = "fake"

    def __init__(self, script=(), *, model=FAKE_MODEL, sleep=time.sleep):
        self.model = model
        self._script = list(script)
        self._sleep = sleep
        self.requests = []

    def __repr__(self):
        return f"FakeProvider(model={self.model!r}, remaining={len(self._script)})"

    @property
    def remaining(self):
        return len(self._script)

    @property
    def calls(self):
        return len(self.requests)

    def add(self, *steps):
        self._script.extend(steps)
        return self

    def generate_json(self, request):
        self.requests.append(request)
        if not self._script:
            raise FakeScriptExhausted(
                f"FakeProvider script exhausted after {len(self.requests) - 1} call(s); "
                "script more replies for this test."
            )
        step = self._script.pop(0)
        if step.delay:
            timeout = request.timeout_seconds
            if timeout is not None and step.delay > timeout:
                self._sleep(timeout)
                raise ProviderTimeout(reason="fake_delay")
            self._sleep(step.delay)
        if isinstance(step, FakeFailure):
            raise ERRORS_BY_CODE[step.code](reason="fake")
        if step.stop_problem is not None:
            raise ProviderInvalidOutput(reason=step.stop_problem)
        data = parse_json_output(step.text)
        return ProviderResult(data=data, usage=step.usage, model=self.model)

    def assert_never_saw(self, *secrets):
        """Fail if any recorded request contains one of `secrets` anywhere."""
        for secret in secrets:
            if not secret:
                continue
            for index, request in enumerate(self.requests):
                if secret in request.model_dump_json():
                    raise AssertionError(f"FakeProvider request {index} contains a secret")
