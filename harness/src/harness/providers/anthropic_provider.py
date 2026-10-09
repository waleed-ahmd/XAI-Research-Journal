"""Anthropic (Claude) provider.

Parsing is split into a pure function (`parse_anthropic_message`) so it can
be unit-tested against plain dicts without touching the network or the SDK.

Visibility rule (platform.claude.com/docs/en/build-with-claude/thinking,
checked 2026-10-07): no `display` setting ever returns Claude's raw chain
of thought. `display: "summarized"` returns a model-written summary;
`display: "omitted"` (or no thinking block at all) returns nothing. So this
provider can only ever report `reasoning_visibility` of "summary" or
"none" — never "full".
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..config import AnthropicModelConfig
from .base import ProviderResult, ReasoningVisibility
from .rate_limit import RateLimiter


def parse_anthropic_message(message: dict[str, Any]) -> tuple[str, str | None, ReasoningVisibility]:
    content = message.get("content", [])
    thinking_block = next((b for b in content if b.get("type") == "thinking"), None)
    text_block = next((b for b in content if b.get("type") == "text"), None)

    answer_text = text_block["text"] if text_block else ""

    if thinking_block is None:
        return answer_text, None, "none"

    thinking_text = thinking_block.get("thinking") or ""
    if thinking_text:
        return answer_text, thinking_text, "summary"
    return answer_text, None, "none"


class AnthropicProvider:
    name = "anthropic"

    def __init__(
        self,
        model_cfg: AnthropicModelConfig,
        *,
        calls_per_minute: float = 20.0,
        max_attempts: int = 5,
    ) -> None:
        import anthropic  # local import: optional dependency, only needed for real calls

        self.model_cfg = model_cfg
        self._client = anthropic.Anthropic()
        self._rate_limiter = RateLimiter(calls_per_minute)
        self._max_attempts = max_attempts

    def call(self, prompt: str, *, run_index: int) -> ProviderResult:
        import anthropic

        request_params: dict[str, Any] = {
            "model": self.model_cfg.model_id,
            "max_tokens": self.model_cfg.max_tokens,
            "thinking": self.model_cfg.thinking.model_dump(),
            "messages": [{"role": "user", "content": prompt}],
            # No temperature/top_p/top_k: Claude Sonnet 5.5 rejects any
            # non-default value with a 400 error (see module docstring's
            # source doc, "Sampling parameters").
        }

        @retry(
            retry=retry_if_exception_type(
                (anthropic.APIStatusError, anthropic.APIConnectionError)
            ),
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=60),
            reraise=True,
        )
        def _do_call():
            self._rate_limiter.wait()
            return self._client.messages.create(**request_params)

        response = _do_call()
        raw_response = response.model_dump()
        answer_text, reasoning_text, visibility = parse_anthropic_message(raw_response)

        return ProviderResult(
            requested_model=self.model_cfg.model_id,
            api_model_id=raw_response.get("model", self.model_cfg.model_id),
            request_params=request_params,
            timestamp=datetime.now(UTC).isoformat(),
            raw_response=raw_response,
            answer_text=answer_text,
            reasoning_text=reasoning_text,
            reasoning_visibility=visibility,
        )
