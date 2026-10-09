"""OpenAI provider, via the Responses API.

Parsing is split into a pure function (`parse_openai_response`) so it can
be unit-tested against plain dicts without touching the network or the
SDK.

Visibility rule (developers.openai.com/api/docs/guides/reasoning, checked
2026-10-07): "reasoning tokens are not visible via the API" by default.
Setting `reasoning.summary` opts into a model-written summary, returned
under `output[].summary[].text` on the `reasoning` output item. The raw
chain of thought is never returned, so this provider can only ever report
`reasoning_visibility` of "summary" or "none" — never "full".
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..config import OpenAIModelConfig
from .base import ProviderResult, ReasoningVisibility
from .rate_limit import RateLimiter


def build_request(model_cfg: OpenAIModelConfig, prompt: str) -> dict[str, Any]:
    """Builds the Responses API request params. Pure/offline: no client, no network.

    `reasoning` is passed straight through as the SDK's `Reasoning` TypedDict
    (`effort`, `summary`) — see `openai.types.shared_params.reasoning.Reasoning`
    in the installed SDK (openai==3.26.0).
    """
    return {
        "model": model_cfg.model_id,
        "input": prompt,
        "reasoning": model_cfg.reasoning.model_dump(),
        "max_output_tokens": model_cfg.max_output_tokens,
        # No temperature: unconfirmed whether this reasoning model accepts a
        # non-default value (see harness/README.md), so we omit it rather
        # than guess.
    }


def parse_openai_response(response: dict[str, Any]) -> tuple[str, str | None, ReasoningVisibility]:
    output = response.get("output", [])

    answer_text = ""
    for item in output:
        if item.get("type") == "message":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    answer_text = block.get("text", "")
                    break
            break

    reasoning_item = next((item for item in output if item.get("type") == "reasoning"), None)
    if reasoning_item is None:
        return answer_text, None, "none"

    summary_parts = [
        block.get("text", "")
        for block in reasoning_item.get("summary", [])
        if block.get("type") == "summary_text"
    ]
    reasoning_text = "\n".join(p for p in summary_parts if p)
    if reasoning_text:
        return answer_text, reasoning_text, "summary"
    return answer_text, None, "none"


class OpenAIProvider:
    name = "openai"

    def __init__(
        self,
        model_cfg: OpenAIModelConfig,
        *,
        calls_per_minute: float = 20.0,
        max_attempts: int = 5,
    ) -> None:
        import openai  # local import: optional dependency, only needed for real calls

        if not model_cfg.model_id:
            raise ValueError(
                "models.openai.model_id is unset in config.yaml — the group has not "
                "confirmed the real model id yet (see the TODO comment there). "
                "Refusing to call an unconfirmed model."
            )

        self.model_cfg = model_cfg
        self._client = openai.OpenAI()
        self._rate_limiter = RateLimiter(calls_per_minute)
        self._max_attempts = max_attempts

    def call(self, prompt: str, *, run_index: int) -> ProviderResult:
        import openai

        request_params = build_request(self.model_cfg, prompt)

        @retry(
            retry=retry_if_exception_type(
                (openai.APIStatusError, openai.APIConnectionError)
            ),
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=60),
            reraise=True,
        )
        def _do_call():
            self._rate_limiter.wait()
            return self._client.responses.create(**request_params)

        response = _do_call()
        raw_response = response.model_dump()
        answer_text, reasoning_text, visibility = parse_openai_response(raw_response)

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
