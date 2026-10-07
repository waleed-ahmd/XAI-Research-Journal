"""Cohen's kappa for inter-rater agreement on the coding sheet."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path


def cohens_kappa(labels1: list[str], labels2: list[str]) -> float:
    if len(labels1) != len(labels2):
        raise ValueError("labels1 and labels2 must be the same length")
    n = len(labels1)
    if n == 0:
        raise ValueError("need at least one rated case to compute kappa")

    agree = sum(1 for a, b in zip(labels1, labels2) if a == b)
    observed_agreement = agree / n

    categories = sorted(set(labels1) | set(labels2))
    count1 = Counter(labels1)
    count2 = Counter(labels2)
    expected_agreement = sum(
        (count1[c] / n) * (count2[c] / n) for c in categories
    )

    if expected_agreement == 1.0:
        return 1.0
    return (observed_agreement - expected_agreement) / (1 - expected_agreement)


def kappa_from_coding_sheet(path: Path) -> float:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    rated = [
        r for r in rows if r.get("rater_1_label", "").strip() and r.get("rater_2_label", "").strip()
    ]
    labels1 = [r["rater_1_label"].strip() for r in rated]
    labels2 = [r["rater_2_label"].strip() for r in rated]
    return cohens_kappa(labels1, labels2)
