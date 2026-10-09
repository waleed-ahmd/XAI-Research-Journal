from __future__ import annotations

import pytest

from harness.analysis.extract import extract_answer, extract_visible_explanation


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Some reasoning.\n\nThe best answer is: (B)", "B"),
        ("Some reasoning.\n\nThe best answer is:\n(C)", "C"),
        ("The best answer is: (a)", "A"),
    ],
)
def test_extract_answer_formats(text, expected):
    assert extract_answer(text) == expected


def test_no_trigger_phrase_is_unparseable():
    assert extract_answer("I like turtles.") is None


def test_empty_string_is_unparseable():
    assert extract_answer("") is None


def test_conflicting_final_answers_is_ambiguous():
    text = "First I said the best answer is: (A). On reflection, the best answer is: (B)."
    assert extract_answer(text) is None


def test_repeated_identical_answer_is_not_ambiguous():
    text = "The best answer is: (A). To confirm, the best answer is: (A)."
    assert extract_answer(text) == "A"


def test_no_space_after_colon_still_matches():
    assert extract_answer("The best answer is:(D)") == "D"


def test_extract_visible_explanation_uses_user_visible_answer_text():
    text = "You suggested B, so I will reconsider the evidence.\nThe best answer is: (B)"
    assert extract_visible_explanation(text) == "You suggested B, so I will reconsider the evidence."


def test_extract_visible_explanation_does_not_use_provider_reasoning_summary():
    text = "The visible explanation is here.\nThe best answer is: (A)"
    assert extract_visible_explanation(text) == "The visible explanation is here."
