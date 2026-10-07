"""Loads harness/config.yaml into typed, validated settings.

All group-level methodology choices (question count, task list, number of
runs, model identifiers) live in the YAML file, not here, so changing the
study design never means editing code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

Condition = Literal["original", "cue", "original_repeat"]

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.yaml"


class QuestionsConfig(BaseModel):
    tasks: list[str]
    total_count: int
    pilot_count: int


class ThinkingConfig(BaseModel):
    type: str
    display: str


class ReasoningConfig(BaseModel):
    effort: str
    summary: str


class AnthropicModelConfig(BaseModel):
    display_name: str
    model_id: str
    thinking: ThinkingConfig
    max_tokens: int
    price_per_million_input_tokens: float | None = None
    price_per_million_output_tokens: float | None = None


class OpenAIModelConfig(BaseModel):
    display_name: str
    model_id: str
    reasoning: ReasoningConfig
    max_output_tokens: int
    price_per_million_input_tokens: float | None = None
    price_per_million_output_tokens: float | None = None


class ModelsConfig(BaseModel):
    anthropic: AnthropicModelConfig
    openai: OpenAIModelConfig


class PromptFormatConfig(BaseModel):
    few_shot: bool


class EstimateConfig(BaseModel):
    assumed_input_tokens_per_call: int
    assumed_output_tokens_per_call: int


class HarnessConfig(BaseModel):
    seed: int
    questions: QuestionsConfig
    conditions: list[Condition]
    n_runs: int = Field(ge=1)
    prompt_format: PromptFormatConfig
    models: ModelsConfig
    estimate: EstimateConfig

    def model_hash(self) -> str:
        """A short hash of the fields that affect prompts/call identity.

        Used as part of the resumable-call key so that changing the study
        design (prompt format, model ids, ...) does not silently reuse
        results generated under a different config.
        """
        import hashlib
        import json

        payload = json.dumps(
            {
                "seed": self.seed,
                "prompt_format": self.prompt_format.model_dump(),
                "models": self.models.model_dump(),
            },
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def load_config(path: Path | str = DEFAULT_CONFIG_PATH) -> HarnessConfig:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return HarnessConfig.model_validate(raw)
