"""End-to-end test of `cot-harness dry-run`: selection -> prompts -> mock
provider -> resumable JSONL, all through the CLI, no network."""

from __future__ import annotations

import json

import yaml
from click.testing import CliRunner

from harness.cli import main


def _write_small_config(path, fixture_data_dir):
    config = {
        "seed": 7,
        "questions": {
            "tasks": ["fake_task_a", "fake_task_b"],
            "total_count": 8,
            "pilot_count": 3,
        },
        "conditions": ["original", "cue", "original_repeat"],
        "n_runs": 1,
        "prompt_format": {"few_shot": False},
        "models": {
            "anthropic": {
                "display_name": "Fake Claude",
                "model_id": "fake-claude",
                "thinking": {"type": "adaptive", "display": "summarized"},
                "max_tokens": 1024,
            },
            "openai": {
                "display_name": "Fake GPT",
                "model_id": "fake-gpt",
                "reasoning": {"effort": "medium", "summary": "auto"},
                "max_output_tokens": 1024,
            },
        },
        "estimate": {"assumed_input_tokens_per_call": 100, "assumed_output_tokens_per_call": 100},
    }
    with path.open("w") as f:
        yaml.safe_dump(config, f)


def test_dry_run_end_to_end(tmp_path, fixture_data_dir):
    config_path = tmp_path / "config.yaml"
    _write_small_config(config_path, fixture_data_dir)
    selected_path = tmp_path / "selected_questions.json"
    results_dir = tmp_path / "results"

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "--data-dir",
            str(fixture_data_dir),
            "--selected-path",
            str(selected_path),
            "--results-dir",
            str(results_dir),
            "dry-run",
            "--full",
        ],
    )
    assert result.exit_code == 0, result.output
    assert selected_path.exists()

    results_file = results_dir / "dryrun_mock.jsonl"
    assert results_file.exists()
    lines = [json.loads(line) for line in results_file.read_text().splitlines()]
    # 8 questions x 3 conditions x 1 run x 2 "models" (anthropic, openai are both mocked here)
    assert len(lines) == 8 * 3 * 2
    assert all(line["reasoning_visibility"] == "full" for line in lines)

    # Running again should skip everything (resumable).
    result2 = runner.invoke(
        main,
        [
            "--config",
            str(config_path),
            "--data-dir",
            str(fixture_data_dir),
            "--selected-path",
            str(selected_path),
            "--results-dir",
            str(results_dir),
            "dry-run",
            "--full",
        ],
    )
    assert result2.exit_code == 0, result2.output
    assert "'skipped': 24" in result2.output.replace('"', "'")
    assert "'called': 0" in result2.output.replace('"', "'")
