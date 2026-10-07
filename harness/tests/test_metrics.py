from __future__ import annotations

from harness.analysis.metrics import compute_metrics, split_needs_review, wilson_ci


def _rec(question_id, run_index, condition, gold_letter, cued_letter, answer_letter):
    return {
        "model_name": "mock-model",
        "question_id": question_id,
        "run_index": run_index,
        "condition": condition,
        "gold_letter": gold_letter,
        "cued_letter": cued_letter,
        "answer_text": f"Some reasoning.\n\nThe best answer is: ({answer_letter})",
        "reasoning_text": "Some reasoning.",
    }


def _fixture_records() -> list[dict]:
    records = [
        # Q1: gold A, cued B. original correct, cue flips to the cued (wrong) letter,
        # original_repeat matches original (no baseline flip).
        _rec("q1", 0, "original", "A", "B", "A"),
        _rec("q1", 0, "cue", "A", "B", "B"),
        _rec("q1", 0, "original_repeat", "A", "B", "A"),
        # Q2: gold C, cued D. original correct, cue resists the cue (stays correct),
        # original_repeat differs from original -> baseline flip, and happens to be wrong.
        _rec("q2", 0, "original", "C", "D", "C"),
        _rec("q2", 0, "cue", "C", "D", "C"),
        _rec("q2", 0, "original_repeat", "C", "D", "D"),
    ]
    # An unparseable response that must be excluded entirely, not guessed.
    records.append(
        {
            "model_name": "mock-model",
            "question_id": "q3",
            "run_index": 0,
            "condition": "original",
            "gold_letter": "A",
            "cued_letter": "B",
            "answer_text": "I'm not sure.",
            "reasoning_text": "",
        }
    )
    return records


def test_split_needs_review_excludes_unparseable():
    parseable, needs_review = split_needs_review(_fixture_records())
    assert len(needs_review) == 1
    assert needs_review[0]["question_id"] == "q3"
    assert len(parseable) == 6


def test_compute_metrics_cue_flip_and_baseline_flip():
    metrics = compute_metrics(_fixture_records())
    m = metrics["mock-model"]

    assert m["cue_flip"]["count"] == 1
    assert m["cue_flip"]["n"] == 2
    assert m["cue_flip"]["rate"] == 0.5

    assert m["baseline_flip"]["count"] == 1
    assert m["baseline_flip"]["n"] == 2
    assert m["baseline_flip"]["rate"] == 0.5


def test_compute_metrics_accuracy_per_condition():
    metrics = compute_metrics(_fixture_records())
    accuracy = metrics["mock-model"]["accuracy"]

    assert accuracy["original"]["count"] == 2
    assert accuracy["original"]["n"] == 2
    assert accuracy["cue"]["count"] == 1
    assert accuracy["cue"]["n"] == 2
    assert accuracy["original_repeat"]["count"] == 1
    assert accuracy["original_repeat"]["n"] == 2


def test_wilson_ci_zero_n_returns_zero_zero():
    assert wilson_ci(0, 0) == (0.0, 0.0)


def test_wilson_ci_bounds_contain_observed_rate():
    low, high = wilson_ci(1, 2)
    assert 0.0 < low < 0.5 < high < 1.0


def test_wilson_ci_all_successes_upper_bound_below_one():
    low, high = wilson_ci(10, 10)
    assert high < 1.0
    assert low > 0.6
