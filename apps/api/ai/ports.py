"""The AI provider port (AD-1, AD-9). Framework-free: stdlib and pydantic only.

Teaching code builds a `ProviderRequest`, hands it to `AIService` and gets a `ProviderResult`
back; it never names a vendor, an SDK or a model id.
"""
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProviderRequest(BaseModel):
    """One structured-output call.

    `system_instruction` is trusted text from versioned prompts only. `user_content` is
    untrusted (learner text, pasted code, earlier model output): providers send it as the user
    turn and never concatenate it into the system instruction.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    system_instruction: str = Field(min_length=1)
    user_content: str
    # JSON schema the output must follow.
    response_schema: dict[str, Any]
    request_id: str | None = None
    # Server-generated Step UUID. Providers add it to the (trusted) system instruction, so it must
    # be a real UUID and can never carry free text; it is normalised to canonical form.
    step_id: str | None = None
    max_output_tokens: int = Field(gt=0)
    # Per-attempt HTTP timeout; set by AIService (never past the overall deadline).
    timeout_seconds: float | None = Field(default=None, gt=0)

    @field_validator("step_id", mode="before")
    @classmethod
    def _step_id_must_be_a_uuid(cls, value):
        if value is None:
            return None
        try:
            return str(UUID(str(value)))
        except ValueError:
            raise ValueError("step_id must be a UUID") from None


class Usage(BaseModel):
    """Token counts as reported by the provider; either may be unknown."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    input_tokens: int | None = None
    output_tokens: int | None = None


class ProviderResult(BaseModel):
    """Parsed JSON output. Syntactically JSON, but NOT yet validated against any domain schema."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    data: dict[str, Any] | list[Any]
    usage: Usage = Field(default_factory=Usage)
    model: str


@runtime_checkable
class AIProvider(Protocol):
    """A vendor adapter. Raises only the typed errors from `ai.errors`."""

    # Short provider name ("gemini", "fake") and the configured model id (None if unset).
    name: str
    model: str | None

    def generate_json(self, request: ProviderRequest) -> ProviderResult: ...
