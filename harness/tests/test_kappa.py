from __future__ import annotations

import csv

import pytest

from harness.analysis.kappa import cohens_kappa, kappa_from_coding_sheet


def test_cohens_kappa_known_example():
    # Textbook 2x2 confusion matrix:
    #              rater2=Yes  rater2=No
    # rater1=Yes       20          5
    # rater1=No        10          15
    # po = 35/50 = 0.7 ; pe = 0.5*0.6 + 0.5*0.4 = 0.5 ; kappa = (0.7-0.5)/0.5 = 0.4
    labels1 = ["Yes"] * 25 + ["No"] * 25
    labels2 = ["Yes"] * 20 + ["No"] * 5 + ["Yes"] * 10 + ["No"] * 15
    kappa = cohens_kappa(labels1, labels2)
    assert kappa == pytest.approx(0.4)


def test_cohens_kappa_perfect_agreement():
    labels = ["explicit", "none", "mentions", "explicit", "none"]
    assert cohens_kappa(labels, labels) == 1.0


def test_cohens_kappa_requires_equal_length():
    with pytest.raises(ValueError):
        cohens_kappa(["a"], ["a", "b"])


def test_kappa_from_coding_sheet_ignores_unrated_rows(tmp_path):
    path = tmp_path / "coding_sheet.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["case_id", "reasoning_text", "rater_1_label", "rater_2_label"]
        )
        writer.writeheader()
        writer.writerow({"case_id": "case-001", "reasoning_text": "x", "rater_1_label": "explicit", "rater_2_label": "explicit"})
        writer.writerow({"case_id": "case-002", "reasoning_text": "y", "rater_1_label": "none", "rater_2_label": "none"})
        # Not yet rated — must be excluded, not treated as disagreement.
        writer.writerow({"case_id": "case-003", "reasoning_text": "z", "rater_1_label": "", "rater_2_label": ""})

    kappa = kappa_from_coding_sheet(path)
    assert kappa == 1.0
