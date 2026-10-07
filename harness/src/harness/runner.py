"""Builds the call plan and runs it against a provider, resumably.

Resumability: results are append-only JSONL, one line per call, each
carrying its `key` (see `harness.hashing.call_key`). Before making a
call we check whether its key is already present and skip it if so, so a
crashed or interrupted run can always be restarted with the same command.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .config import Condition, HarnessConfig
from .data.models import Question, SelectedQuestion
from .hashing import call_key
from .prompts import build_prompt
from .providers.base import Provider


@dataclass(frozen=True)
class PlannedCall:
    question: SelectedQuestion
    condition: Condition
    model_name: str
    run_index: int
    key: str
    prompt: str


def build_plan(
    selected: list[SelectedQuestion],
    questions_by_id: dict[str, Question],
    config: HarnessConfig,
    model_name: str,
) -> list[PlannedCall]:
    config_hash = config.model_hash()
    plan: list[PlannedCall] = []
    for sq in selected:
        question = questions_by_id[f"{sq.task}:{sq.idx}"]
        for condition in config.conditions:
            prompt = build_prompt(question, condition, sq.cued_letter)
            for run_index in range(config.n_runs):
                key = call_key(
                    question_id=question.question_id,
                    condition=condition,
                    model_name=model_name,
                    run_index=run_index,
                    config_hash=config_hash,
                )
                plan.append(
                    PlannedCall(
                        question=sq,
                        condition=condition,
                        model_name=model_name,
                        run_index=run_index,
                        key=key,
                        prompt=prompt,
                    )
                )
    return plan


def load_existing_keys(results_path: Path) -> set[str]:
    results_path = Path(results_path)
    if not results_path.exists():
        return set()
    keys: set[str] = set()
    with results_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            keys.add(json.loads(line)["key"])
    return keys


def append_result(results_path: Path, record: dict) -> None:
    results_path = Path(results_path)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


class SupportsCall(Protocol):
    def call(self, prompt: str, *, run_index: int) -> object: ...


def run_plan(plan: list[PlannedCall], provider: Provider, results_path: Path) -> dict[str, int]:
    """Executes `plan` against `provider`, skipping already-completed keys.

    Returns a small summary: {"skipped": n, "called": n}.
    """
    existing = load_existing_keys(results_path)
    skipped = 0
    called = 0
    for pc in plan:
        if pc.key in existing:
            skipped += 1
            continue
        result = provider.call(pc.prompt, run_index=pc.run_index)
        record = {
            "key": pc.key,
            "question_id": f"{pc.question.task}:{pc.question.idx}",
            "task": pc.question.task,
            "idx": pc.question.idx,
            "condition": pc.condition,
            "model_name": pc.model_name,
            "run_index": pc.run_index,
            "gold_letter": pc.question.gold_letter,
            "cued_letter": pc.question.cued_letter,
            "prompt": pc.prompt,
            **result.model_dump(),
        }
        append_result(results_path, record)
        called += 1
    return {"skipped": skipped, "called": called}
