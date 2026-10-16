from __future__ import annotations

from harness.data.loader import load_all_questions
from harness.data.selection import select_questions
from harness.providers.mock import MockProvider
from harness.runner import build_plan, load_existing_keys, run_plan


def _questions_by_id(config, data_dir):
    return {q.question_id: q for q in load_all_questions(config.questions.tasks, data_dir)}


def test_resume_skips_already_completed_calls(small_config, fixture_data_dir, tmp_path):
    selected = select_questions(small_config, fixture_data_dir)
    questions_by_id = _questions_by_id(small_config, fixture_data_dir)
    plan = build_plan(selected, questions_by_id, small_config, "mock")

    results_path = tmp_path / "mock.jsonl"
    provider = MockProvider()

    first_summary = run_plan(plan, provider, results_path)
    assert first_summary == {"skipped": 0, "called": len(plan)}
    assert provider.call_count == len(plan)

    # Re-running the identical plan should skip every call.
    second_summary = run_plan(plan, provider, results_path)
    assert second_summary == {"skipped": len(plan), "called": 0}
    assert provider.call_count == len(plan)  # unchanged


def test_resume_only_calls_for_missing_keys(small_config, fixture_data_dir, tmp_path):
    selected = select_questions(small_config, fixture_data_dir)
    questions_by_id = _questions_by_id(small_config, fixture_data_dir)
    plan = build_plan(selected, questions_by_id, small_config, "mock")

    results_path = tmp_path / "mock.jsonl"
    provider = MockProvider()

    # Simulate a partial prior run: only run the first half of the plan.
    half = len(plan) // 2
    run_plan(plan[:half], provider, results_path)
    existing_after_partial = load_existing_keys(results_path)
    assert len(existing_after_partial) == half

    summary = run_plan(plan, provider, results_path)
    assert summary["skipped"] == half
    assert summary["called"] == len(plan) - half
    assert load_existing_keys(results_path) == {pc.key for pc in plan}


def test_call_keys_change_when_selected_question_set_changes(small_config, fixture_data_dir):
    selected = select_questions(small_config, fixture_data_dir)
    questions_by_id = _questions_by_id(small_config, fixture_data_dir)
    baseline = build_plan(selected, questions_by_id, small_config, "mock")

    changed = list(selected)
    changed[0] = changed[0].model_copy(update={"cued_letter": "Z"})
    altered = build_plan(changed, questions_by_id, small_config, "mock")

    assert baseline[0].key != altered[0].key


def test_prompt_edit_changes_keys(small_config, fixture_data_dir, monkeypatch):
    from harness import prompts
    selected = select_questions(small_config, fixture_data_dir)
    questions = _questions_by_id(small_config, fixture_data_dir)
    before = build_plan(selected, questions, small_config, 'mock')
    monkeypatch.setattr(prompts, 'VISIBLE_EXPLANATION_INSTRUCTION', 'New output instruction')
    after = build_plan(selected, questions, small_config, 'mock')
    assert {p.key for p in before}.isdisjoint(p.key for p in after)


def test_pricing_and_display_edits_reuse_keys(small_config, fixture_data_dir):
    selected = select_questions(small_config, fixture_data_dir)
    questions = _questions_by_id(small_config, fixture_data_dir)
    before = build_plan(selected, questions, small_config, 'mock')
    changed = small_config.model_copy(deep=True)
    changed.models.openai.price_per_million_input_tokens = 999
    changed.models.anthropic.price_per_million_output_tokens = 999
    changed.models.openai.display_name = 'New label'
    assert [p.key for p in before] == [p.key for p in build_plan(selected, questions, changed, 'mock')]
