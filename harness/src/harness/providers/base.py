"""Provider interface shared by Anthropic, OpenAI and the Mock provider.

`reasoning_visibility` is load-bearing: the study can only claim things
about reasoning that is actually visible in the response, so every
provider must set it honestly based on what the API actually returned,
never assume "full".
"""

from __future__ import annotations

from typing import Any, Literal, Protocol

from pydantic import BaseModel

ReasoningVisibility = Literal["full", "summary", "none"]


class ProviderResult(BaseModel):
    requested_model: str
    api_model_id: str
    request_params: dict[str, Any]
    timestamp: str  # ISO 8601, UTC
    raw_response: dict[str, Any]
    answer_text: str
    reasoning_text: str | None
    reasoning_visibility: ReasoningVisibility


class Provider(Protocol):
    name: str

    def call(self, prompt: str, *, run_index: int) -> ProviderResult: ...
