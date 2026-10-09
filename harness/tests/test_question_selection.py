from __future__ import annotations

from harness.data.selection import select_questions


def test_selection_is_reproducible_from_seed(small_config, fixture_data_dir):
    first = select_questions(small_config, fixture_data_dir)
    second = select_questions(small_config, fixture_data_dir)
    assert [s.model_dump() for s in first] == [s.model_dump() for s in second]


def test_selection_respects_total_count(small_config, fixture_data_dir):
    selected = select_questions(small_config, fixture_data_dir)
    assert len(selected) == small_config.questions.total_count


def test_selection_changes_with_seed(small_config, fixture_data_dir):
    baseline = select_questions(small_config, fixture_data_dir)

    other = small_config.model_copy(deep=True)
    other.seed = small_config.seed + 1
    changed = select_questions(other, fixture_data_dir)

    baseline_ids = [(s.task, s.idx) for s in baseline]
    changed_ids = [(s.task, s.idx) for s in changed]
    assert baseline_ids != changed_ids


def test_selection_errors_if_not_enough_candidates(small_config, fixture_data_dir):
    import pytest

    too_big = small_config.model_copy(deep=True)
    too_big.questions.total_count = 10_000
    with pytest.raises(ValueError):
        select_questions(too_big, fixture_data_dir)


def test_write_and_load_round_trip(small_config, fixture_data_dir, tmp_path):
    from harness.data.selection import load_selected_questions, write_selected_questions

    selected = select_questions(small_config, fixture_data_dir)
    out_path = tmp_path / "selected_questions.json"
    write_selected_questions(selected, out_path)
    loaded = load_selected_questions(out_path)
    assert [s.model_dump() for s in loaded] == [s.model_dump() for s in selected]


def test_config_hash_changes_when_protocol_or_task_changes(small_config):
    baseline = small_config.model_hash()

    changed_protocol = small_config.model_copy(deep=True)
    changed_protocol.protocol_version = "test-v2"
    assert changed_protocol.model_hash() != baseline

    changed_task = small_config.model_copy(deep=True)
    changed_task.questions.tasks = ["fake_task_a"]
    assert changed_task.model_hash() != baseline
