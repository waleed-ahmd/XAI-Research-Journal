"""Deterministic mock provider. Used in every test and by `dry-run`.

Never calls a network API. The "answer" is derived from a hash of the
prompt text so different questions/conditions get different (but fully
reproducible) answers, which lets dry-run/integration tests exercise
answer-flip detection without real model calls.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from string import ascii_uppercase

from .base import ProviderResult


class MockProvider:
    name = "mock"

    def __init__(self, model_id: str = "mock-model-v1", num_choices: int = 4) -> None:
        self.model_id = model_id
        self.num_choices = num_choices
        self.call_count = 0

    def call(self, prompt: str, *, run_index: int) -> ProviderResult:
        self.call_count += 1
        digest = hashlib.sha256(f"{prompt}|{run_index}".encode("utf-8")).hexdigest()
        letter = ascii_uppercase[int(digest[:8], 16) % self.num_choices]
        reasoning_text = (
            "Mock reasoning: breaking the question into steps and checking "
            "each option before committing to an answer."
        )
        answer_text = f"{reasoning_text}\n\nThe best answer is: ({letter})"
        return ProviderResult(
            requested_model=self.model_id,
            api_model_id=self.model_id,
            request_params={"prompt_chars": len(prompt), "run_index": run_index},
            timestamp=datetime.now(UTC).isoformat(),
            raw_response={"mock": True, "answer_text": answer_text},
            answer_text=answer_text,
            reasoning_text=reasoning_text,
            reasoning_visibility="full",
        )
