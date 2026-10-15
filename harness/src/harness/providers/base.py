"""Provider interface shared by Anthropic, OpenAI and the Mock provider.

`reasoning_visibility` is load-bearing: the study can only claim things
about reasoning that is actually visible in the response, so every
provider must set it honestly based on what the API actually returned,
never assume "full".
"""

from __future__ import annotations

from typing import Any, Callable, Literal, Protocol, TypeVar

from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .rate_limit import RateLimiter

ReasoningVisibility = Literal["full", "summary", "none"]

T = TypeVar("T")


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


def retrying_call(
    fn: Callable[[], T],
    *,
    rate_limiter: RateLimiter,
    exception_types: tuple[type[Exception], ...],
    max_attempts: int,
) -> T:
    """Waits on `rate_limiter`, then calls `fn()`, retrying on `exception_types`
    with exponential backoff (1s, capped at 60s) and reraising the final error.

    Shared by the real providers so backoff policy lives in one place.
    """

    @retry(
        retry=retry_if_exception_type(exception_types),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        reraise=True,
    )
    def _do_call() -> T:
        rate_limiter.wait()
        return fn()

    return _do_call()
