"""The resumable-call key: hash of (question, condition, model, run index, config)."""

from __future__ import annotations

import hashlib


def call_key(
    *,
    question_id: str,
    condition: str,
    model_name: str,
    run_index: int,
    config_hash: str,
) -> str:
    payload = f"{question_id}|{condition}|{model_name}|{run_index}|{config_hash}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
