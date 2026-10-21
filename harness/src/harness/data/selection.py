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
from .loader import load_all_questions, question_index, resolve_question
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
                fingerprint=q.question_fingerprint,
                num_choices=q.num_choices,
                gold_letter=q.gold_letter,
                cued_letter=cued_letter,
            )
        )
    return selected


def select_questions_balanced(
    config: HarnessConfig,
    data_dir: Path,
    *,
    existing_question_ids: set[str] | None = None,
    existing_question_fingerprints: dict[str, str] | None = None,
    existing_question_cues: dict[str, str] | None = None,
) -> list[SelectedQuestion]:
    """Select a balanced fixed set, preserving already-completed question IDs.

    This is intended for the expanded all-Turpin-task run. `counts_by_task`
    defines the final quota for each task. Existing IDs are included first, so
    previously paid experiments are reused rather than rerun. Remaining slots
    are sampled deterministically from questions not already completed.
    """
    counts = config.questions.counts_by_task
    if counts is None:
        raise ValueError("Balanced selection requires questions.counts_by_task in the config")

    existing_question_cues = existing_question_cues or {}
    existing_question_ids = existing_question_ids or set()
    existing_question_fingerprints = existing_question_fingerprints or {}
    candidates = list({(q.task, q.question_fingerprint): q for q in load_all_questions(config.questions.tasks, data_dir)}.values())
    by_task: dict[str, list[Question]] = {task: [] for task in config.questions.tasks}
    for q in candidates:
        by_task[q.task].append(q)
    for task in by_task:
        by_task[task].sort(key=lambda q: q.idx)

    selected_questions: list[Question] = []
    preserved = set()
    rng_seed = config.seed
    for task in config.questions.tasks:
        quota = counts[task]
        task_candidates = by_task[task]
        existing = []
        for q in task_candidates:
            if q.question_id not in existing_question_ids:
                continue
            fingerprint = existing_question_fingerprints.get(q.question_id)
            if fingerprint is None or fingerprint == q.question_fingerprint:
                existing.append(q)
        required = {qid for qid in existing_question_ids if qid.startswith(task + ":")}
        missing = required - {q.question_id for q in existing}
        if missing:
            raise ValueError(f"Historical question content missing or changed: {sorted(missing)}")
        if any(sum(q.question_id == qid for q in existing) > 1 for qid in required):
            raise ValueError("Historical duplicate IDs require exact fingerprints")
        if len(existing) > quota:
            raise ValueError(
                f"{task} already has {len(existing)} completed questions but its target quota is {quota}"
            )
        preserved.update((q.task, q.question_fingerprint) for q in existing)
        chosen = list(existing)
        remaining = [q for q in task_candidates if q.question_fingerprint not in {x.question_fingerprint for x in chosen}]
        if len(remaining) < quota - len(chosen):
            raise ValueError(
                f"Only {len(task_candidates)} questions are available for {task}, "
                f"but quota is {quota}"
            )
        random.Random(f"{rng_seed}:{task}").shuffle(remaining)
        chosen.extend(remaining[: quota - len(chosen)])
        selected_questions.extend(chosen)

    # Keep task order stable, then shuffle within the whole fixed set using the
    # study seed so both providers receive the same question order.
    rng = random.Random(config.seed)
    rng.shuffle(selected_questions)

    selected: list[SelectedQuestion] = []
    for i, q in enumerate(selected_questions):
        cue = choose_cue_letter(q.task, q.idx, q.gold_letter, q.num_choices, config.seed)
        if (q.task, q.question_fingerprint) in preserved:
            cue = existing_question_cues.get(q.question_id, cue)
        selected.append(
            SelectedQuestion(
                index=i,
                task=q.task,
                idx=q.idx,
                fingerprint=q.question_fingerprint,
                num_choices=q.num_choices,
                gold_letter=q.gold_letter,
                cued_letter=cue,
            )
        )
    return selected


def question_ids_from_results(results_dir: Path) -> set[str]:
    """Collect question IDs that already have real results in JSONL files."""
    from ..jsonl import read_jsonl

    found: set[str] = set()
    for path in sorted(Path(results_dir).glob("*.jsonl")):
        if path.name == "dryrun_mock.jsonl":
            continue
        for record in read_jsonl(path):
            question_id = record.get("question_id")
            if question_id:
                found.add(":".join(question_id.split(":")[:2]))
    return found


def question_fingerprints_from_results(results_dir: Path) -> dict[str, str]:
    """Recover exact question fingerprints from historical original prompts."""
    from ..jsonl import read_jsonl
    from ..prompts import VISIBLE_EXPLANATION_INSTRUCTION
    import hashlib

    suffix = "\n\n" + VISIBLE_EXPLANATION_INSTRUCTION
    found: dict[str, str] = {}
    for path in sorted(Path(results_dir).glob("*.jsonl")):
        if path.name == "dryrun_mock.jsonl":
            continue
        for record in read_jsonl(path):
            if record.get("condition") != "original":
                continue
            question_id = record.get("question_id")
            prompt = record.get("prompt", "")
            if question_id and prompt.endswith(suffix):
                parsed = prompt[:-len(suffix)]
                normalized = "\n".join(line.rstrip() for line in parsed.strip().splitlines())
                found.setdefault(":".join(question_id.split(":")[:2]), hashlib.sha256(normalized.encode("utf-8")).hexdigest())
    return found


def question_ids_from_manifest(path: Path) -> set[str]:
    """Load completed question IDs recorded by earlier experiment artifacts."""
    path = Path(path)
    if not path.exists():
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("questions"):
        return {str(qid) for qid in payload["questions"]}
    return {str(qid) for qid in payload.get("question_ids", [])}


def question_fingerprints_from_manifest(path: Path) -> dict[str, str]:
    """Load exact completed-question fingerprints from the project manifest."""
    path = Path(path)
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(qid): str(value["fingerprint"]) for qid, value in payload.get("questions", {}).items() if value.get("fingerprint")}


def write_selected_questions(selected: list[SelectedQuestion], out_path: Path) -> None:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump([s.model_dump() for s in selected], f, indent=2)


def load_selected_questions(path: Path) -> list[SelectedQuestion]:
    with Path(path).open("r", encoding="utf-8") as f:
        raw = json.load(f)
    return [SelectedQuestion.model_validate(r) for r in raw]


def selection_settings(config: HarnessConfig) -> dict:
    return {"seed": config.seed, "tasks": config.questions.tasks,
            "total_count": config.questions.total_count,
            "counts_by_task": config.questions.counts_by_task}


def validate_saved_selection(selected, config, data_dir, selected_path):
    """Fail closed on stale selections; legacy lists must match seeded selection."""
    metadata = Path(str(selected_path) + ".metadata.json")
    if metadata.exists():
        saved = json.loads(metadata.read_text())
        historical = saved.pop("historical_questions", {})
        saved.setdefault("counts_by_task", None)
        if saved != selection_settings(config):
            raise ValueError("Selected-question settings changed (seed/tasks/total_count). Use a new --selected-path.")
    elif [s.model_dump(exclude={"fingerprint"}) for s in selected] != [s.model_dump(exclude={"fingerprint"}) for s in select_questions(config, data_dir)]:
        raise ValueError("Legacy selected questions do not match the current seeded selection. Use a new --selected-path.")
    historical = historical if metadata.exists() else {}
    questions = question_index(load_all_questions(config.questions.tasks, data_dir))
    if len(selected) != config.questions.total_count or len({s.question_id for s in selected}) != len(selected):
        raise ValueError("Selected-question count or uniqueness does not match config.")
    for i, s in enumerate(selected):
        q = resolve_question(s, questions)
        previous = historical.get(s.source_question_id, {})
        cue = choose_cue_letter(s.task, s.idx, q.gold_letter, q.num_choices, config.seed)
        if previous.get("fingerprint") == q.question_fingerprint:
            cue = previous.get("cued_letter", cue)
        if s.index != i or s.gold_letter != q.gold_letter or s.num_choices != q.num_choices or s.cued_letter != cue or s.cued_letter == q.gold_letter or s.cued_letter not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[:q.num_choices]:
            raise ValueError("Selected-question data does not match the current dataset/config.")
    if config.questions.counts_by_task is not None:
        from collections import Counter
        actual = Counter(s.task for s in selected)
        if dict(actual) != config.questions.counts_by_task:
            raise ValueError("Selected-question per-task counts do not match the current config.")
