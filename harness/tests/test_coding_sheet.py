from __future__ import annotations

from harness.analysis.coding_sheet import build_coding_sheet


def _rec(question_id, condition, gold, cued, answer, model="m", reasoning="reasoning text"):
    return {
        "model_name": model,
        "question_id": question_id,
        "run_index": 0,
        "condition": condition,
        "gold_letter": gold,
        "cued_letter": cued,
        "answer_text": f"{reasoning}\n\nThe best answer is: ({answer})",
        "reasoning_text": reasoning,
    }


def test_coding_sheet_only_contains_cue_flipped_cases():
    records = [
        _rec("q1", "original", "A", "B", "A"),
        _rec("q1", "cue", "A", "B", "B"),  # flips to cued -> included
        _rec("q2", "original", "A", "B", "A"),
        _rec("q2", "cue", "A", "B", "A"),  # resists cue -> excluded
    ]
    sheet_rows, key_rows = build_coding_sheet(records, seed=1)
    assert len(sheet_rows) == 1
    assert key_rows[0]["question_id"] == "q1"


def test_coding_sheet_hides_model_name():
    records = [
        _rec("q1", "original", "A", "B", "A"),
        _rec("q1", "cue", "A", "B", "B"),
    ]
    sheet_rows, _ = build_coding_sheet(records, seed=1)
    assert "model_name" not in sheet_rows[0]


def test_coding_sheet_has_blank_rater_columns():
    records = [
        _rec("q1", "original", "A", "B", "A"),
        _rec("q1", "cue", "A", "B", "B"),
    ]
    sheet_rows, _ = build_coding_sheet(records, seed=1)
    assert sheet_rows[0]["rater_1_label"] == ""
    assert sheet_rows[0]["rater_2_label"] == ""


def test_coding_sheet_shuffle_is_deterministic():
    records = [
        _rec(f"q{i}", "original", "A", "B", "A") for i in range(5)
    ] + [_rec(f"q{i}", "cue", "A", "B", "B") for i in range(5)]
    first, _ = build_coding_sheet(records, seed=99)
    second, _ = build_coding_sheet(records, seed=99)
    assert first == second
