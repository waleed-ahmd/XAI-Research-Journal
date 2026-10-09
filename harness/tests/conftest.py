from __future__ import annotations

from pathlib import Path

import pytest

from harness.config import HarnessConfig

FIXTURES_DATA_DIR = Path(__file__).parent / "fixtures" / "bbh"


@pytest.fixture
def fixture_data_dir() -> Path:
    return FIXTURES_DATA_DIR


@pytest.fixture
def small_config() -> HarnessConfig:
    return HarnessConfig.model_validate(
        {
            "protocol_version": "test-v1",
            "seed": 42,
            "questions": {
                "tasks": ["fake_task_a", "fake_task_b"],
                "total_count": 10,
                "pilot_count": 3,
            },
            "conditions": ["original", "cue", "original_repeat"],
            "n_runs": 1,
            "prompt_format": {"few_shot": False, "explanation_mode": "visible_explanation"},
            "models": {
                "anthropic": {
                    "display_name": "Fake Claude",
                    "model_id": "fake-claude",
                    "thinking": {"type": "adaptive", "display": "summarized"},
                    "effort": "high",
                    "max_tokens": 1024,
                },
                "openai": {
                    "display_name": "Fake GPT",
                    "model_id": "fake-gpt",
                    "reasoning": {"effort": "medium", "summary": "auto"},
                    "max_output_tokens": 1024,
                },
            },
            "estimate": {
                "assumed_input_tokens_per_call": 100,
                "assumed_output_tokens_per_call": 100,
            },
        }
    )
