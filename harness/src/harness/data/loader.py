"""Loads BBH questions from locally cached val_data.json files.

We never invent questions: every item comes from Turpin et al.'s released
data (github.com/milesaturpin/cot-unfaithfulness, MIT licensed — see
harness/README.md). Use `harness.data.fetch` to populate the cache from
GitHub, or point `data_dir` at test fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import Question


def load_task_questions(task: str, data_dir: Path) -> list[Question]:
    path = Path(data_dir) / task / "val_data.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No cached data for task '{task}' at {path}. "
            "Run `cot-harness fetch-data` first (requires network, no API cost)."
        )
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    # val_data.json is {"canary": "<BIG-Bench canary GUID>", "data": [...]}, not a bare list.
    rows = raw["data"]
    # A few tasks (e.g. logical_deduction_five_objects, web_of_lies) ship rows with no
    # "idx" field. Fall back to list position — stable across loads of the same file.
    return [
        Question.model_validate(row | {"task": task, "idx": row.get("idx", position)})
        for position, row in enumerate(rows)
    ]


def load_all_questions(tasks: list[str], data_dir: Path) -> list[Question]:
    questions: list[Question] = []
    for task in tasks:
        questions.extend(load_task_questions(task, data_dir))
    return questions
