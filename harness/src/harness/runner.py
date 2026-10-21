"""Builds the call plan and runs it against a provider, resumably.

Resumability: results are append-only JSONL, one line per call, each
carrying its `key` (see `harness.hashing.call_key`). Before making a
call we check whether its key is already present and skip it if so, so a
crashed or interrupted run can always be restarted with the same command.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
import hashlib
from pathlib import Path

from .config import Condition, HarnessConfig
from .data.models import Question, SelectedQuestion
from .data.loader import resolve_question
from .hashing import call_key
from .jsonl import read_jsonl
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


def _selected_questions_hash(selected: list[SelectedQuestion]) -> str:
    """Hash the exact selected question IDs and cue letters used by the run."""
    import hashlib
    import json

    payload = json.dumps(
        [s.model_dump() for s in selected],
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def build_plan(
    selected: list[SelectedQuestion],
    questions_by_id: dict[str, Question],
    config: HarnessConfig,
    model_name: str,
) -> list[PlannedCall]:
    config_hash = config.model_hash()
    selected_hash = _selected_questions_hash(selected)
    plan: list[PlannedCall] = []
    for sq in selected:
        question = resolve_question(sq, questions_by_id)
        for condition in config.conditions:
            prompt = build_prompt(
                question,
                condition,
                sq.cued_letter,
                explanation_mode=config.prompt_format.explanation_mode,
            )
            for run_index in range(config.n_runs):
                key = call_key(
                    question_id=sq.question_id,
                    condition=condition,
                    model_name=model_name,
                    run_index=run_index,
                    config_hash=f"{config_hash}:{selected_hash}:{hashlib.sha256(prompt.encode()).hexdigest()}",
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
    return {record["key"] for record in read_jsonl(results_path)}


def append_result(results_path: Path, record: dict) -> None:
    results_path = Path(results_path)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with results_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


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
            "question_id": pc.question.question_id,
            "source_question_id": pc.question.source_question_id,
            "question_fingerprint": pc.question.fingerprint,
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
