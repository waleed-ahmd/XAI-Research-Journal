"""Reproducible selection of the fixed question set.

Given the configured seed, task list and total_count, always picks the
same questions in the same order, so `harness/data/selected_questions.json`
is a record of exactly which items were used — not just a count.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from ..config import HarnessConfig
from ..cue import choose_cue_letter
from .loader import load_all_questions
from .models import Question, SelectedQuestion


def select_questions(config: HarnessConfig, data_dir: Path) -> list[SelectedQuestion]:
    candidates: list[Question] = sorted(
        load_all_questions(config.questions.tasks, data_dir),
        key=lambda q: (q.task, q.idx),
    )
    if len(candidates) < config.questions.total_count:
        raise ValueError(
            f"Only {len(candidates)} candidate questions available across "
            f"{config.questions.tasks}, but total_count is {config.questions.total_count}"
        )

    rng = random.Random(config.seed)
    sampled = rng.sample(candidates, config.questions.total_count)

    selected: list[SelectedQuestion] = []
    for i, q in enumerate(sampled):
        cued_letter = choose_cue_letter(
            q.task, q.idx, q.gold_letter, q.num_choices, config.seed
        )
        selected.append(
            SelectedQuestion(
                index=i,
                task=q.task,
                idx=q.idx,
                num_choices=q.num_choices,
                gold_letter=q.gold_letter,
                cued_letter=cued_letter,
            )
        )
    return selected


def write_selected_questions(selected: list[SelectedQuestion], out_path: Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump([s.model_dump() for s in selected], f, indent=2)


def load_selected_questions(path: Path) -> list[SelectedQuestion]:
    with Path(path).open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return [SelectedQuestion.model_validate(r) for r in raw]
