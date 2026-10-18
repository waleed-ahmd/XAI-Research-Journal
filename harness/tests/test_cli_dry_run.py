"""End-to-end test of `cot-harness dry-run`: selection -> prompts -> mock
provider -> resumable JSONL, all through the CLI, no network."""

from __future__ import annotations

import json

import yaml
from click.testing import CliRunner

from harness.cli import main


def _write_small_config(path, fixture_data_dir):
    config = {
        "protocol_version": "test-v1",
        "seed": 7,
        "questions": {
            "tasks": ["fake_task_a", "fake_task_b"],
            "total_count": 8,
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


def test_selection_rejects_changed_settings(tmp_path, fixture_data_dir, small_config):
    import pytest
    from harness.cli import _get_or_select_questions
    import click
    path = tmp_path / 'selected.json'
    _get_or_select_questions(small_config, fixture_data_dir, path)
    for field, value in [('seed', small_config.seed + 1), ('total_count', 2), ('tasks', ['fake_task_a'])]:
        changed = small_config.model_copy(deep=True)
        if field == 'seed': changed.seed = value
        else: setattr(changed.questions, field, value)
        with pytest.raises(click.ClickException, match='settings changed'):
            _get_or_select_questions(changed, fixture_data_dir, path)


def test_analyze_excludes_mock_results(tmp_path, small_config, monkeypatch):
    import sys
    from types import SimpleNamespace
    from harness import cli
    data = tmp_path / 'raw'
    data.mkdir()
    # No matplotlib cache or figure rendering needed for this ingestion regression.
    monkeypatch.setitem(sys.modules, 'harness.analysis.figures', SimpleNamespace(
        plot_accuracy=lambda *args: None, plot_flip_rates=lambda *args: None))
    monkeypatch.setattr(cli, 'DEFAULT_SUMMARY_DIR', tmp_path / 'summary')
    config_path = tmp_path / 'config.yaml'
    config_path.write_text(yaml.safe_dump(small_config.model_dump()))
    fake = dict(model_name='fake', question_id='fake:0', condition='original', run_index=0,
                gold_letter='A', cued_letter='B', answer_text='The best answer is: (B)')
    (data / 'dryrun_mock.jsonl').write_text(json.dumps(fake) + '\n')
    real = {**fake, 'model_name': 'real', 'answer_text': 'The best answer is: (A)'}
    (data / 'openai.jsonl').write_text(json.dumps(real) + '\n')
    result = CliRunner().invoke(main, ['--config', str(config_path), '--results-dir', str(data), 'analyze'])
    assert result.exit_code == 0, result.output
    summary = (tmp_path / 'summary/metrics_summary.csv').read_text()
    assert 'real' in summary and 'fake' not in summary
