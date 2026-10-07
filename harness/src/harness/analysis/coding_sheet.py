"""Builds the human coding sheet for cue-acknowledgement rating.

Cue acknowledgement is judged by humans, not an LLM (hard rule). This
module only prepares the sheet: it selects the cue-flipped cases (same
definition as `metrics.compute_metrics`'s cue_flip), shuffles them with a
seeded RNG, and hides the model name so raters can't tell which model
produced which reasoning. A separate, non-public key file records the
case_id -> model_name/question_id mapping for rejoining after rating.
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path

from .extract import extract_visible_explanation
from .metrics import split_needs_review


def build_coding_sheet(records: list[dict], seed: int) -> tuple[list[dict], list[dict]]:
    """Returns (sheet_rows, key_rows)."""
    parseable, _ = split_needs_review(records)

    by_model_question: dict[tuple[str, str, int], dict[str, dict]] = defaultdict(dict)
    for r in parseable:
        key = (r["model_name"], r["question_id"], r["run_index"])
        by_model_question[key][r["condition"]] = r

    flip_cases: list[dict] = []
    for (model_name, question_id, run_index), conds in sorted(by_model_question.items()):
        if "original" not in conds or "cue" not in conds:
            continue
        original_rec = conds["original"]
        cue_rec = conds["cue"]
        cued_letter = cue_rec["cued_letter"]
        if cue_rec["parsed_answer"] != cued_letter:
            continue
        if original_rec["parsed_answer"] == cue_rec["parsed_answer"]:
            continue
        flip_cases.append(
            {
                "model_name": model_name,
                "question_id": question_id,
                "run_index": run_index,
                "original_answer": original_rec["parsed_answer"],
                "cue_answer": cue_rec["parsed_answer"],
                "cued_letter": cued_letter,
                "visible_explanation": extract_visible_explanation(cue_rec.get("answer_text") or ""),
            }
        )

    random.Random(seed).shuffle(flip_cases)

    sheet_rows: list[dict] = []
    key_rows: list[dict] = []
    for i, case in enumerate(flip_cases, start=1):
        case_id = f"case-{i:03d}"
        sheet_rows.append(
            {
                "case_id": case_id,
                "visible_explanation": case["visible_explanation"],
                "rater_1_label": "",
                "rater_2_label": "",
                # Optional LLM pre-label: clearly marked, excluded from reported
                # metrics (see harness/ACKNOWLEDGEMENT_RUBRIC.md).
                "llm_pre_label_DO_NOT_USE_IN_METRICS": "",
            }
        )
        key_rows.append(
            {
                "case_id": case_id,
                "model_name": case["model_name"],
                "question_id": case["question_id"],
                "run_index": case["run_index"],
                "original_answer": case["original_answer"],
                "cue_answer": case["cue_answer"],
                "cued_letter": case["cued_letter"],
            }
        )
    return sheet_rows, key_rows


def write_csv(rows: list[dict], out_path: Path, fieldnames: list[str]) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
