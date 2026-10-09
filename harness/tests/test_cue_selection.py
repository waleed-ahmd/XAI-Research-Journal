from __future__ import annotations

from harness.cue import choose_cue_letter
from harness.data.loader import load_all_questions


def test_cue_never_equals_gold(fixture_data_dir):
    questions = load_all_questions(["fake_task_a", "fake_task_b"], fixture_data_dir)
    assert len(questions) > 0
    for q in questions:
        for seed in (0, 1, 42, 20261007):
            cued = choose_cue_letter(q.task, q.idx, q.gold_letter, q.num_choices, seed)
            assert cued != q.gold_letter


def test_cue_is_a_valid_choice_letter(fixture_data_dir):
    questions = load_all_questions(["fake_task_a", "fake_task_b"], fixture_data_dir)
    from string import ascii_uppercase

    for q in questions:
        cued = choose_cue_letter(q.task, q.idx, q.gold_letter, q.num_choices, seed=7)
        assert cued in ascii_uppercase[: q.num_choices]


def test_cue_selection_is_deterministic(fixture_data_dir):
    questions = load_all_questions(["fake_task_a", "fake_task_b"], fixture_data_dir)
    q = questions[0]
    first = choose_cue_letter(q.task, q.idx, q.gold_letter, q.num_choices, seed=123)
    second = choose_cue_letter(q.task, q.idx, q.gold_letter, q.num_choices, seed=123)
    assert first == second


def test_rejects_single_choice_question():
    import pytest

    with pytest.raises(ValueError):
        choose_cue_letter("t", 0, "A", 1, seed=1)
