"""Offline Batch planning and estimated costs, independent of the CLI/UI."""
from __future__ import annotations

import json

from .batch import pending_batch_keys
from .data.selection import question_ids_from_manifest, question_fingerprints_from_manifest
from .runner import build_plan, load_existing_keys


def estimate_batch_cost(config, model_name, n_calls):
    import math
    cfg = getattr(config.models, model_name)
    if not n_calls:
        return 0.0
    prices = (cfg.price_per_million_input_tokens, cfg.price_per_million_output_tokens)
    if any(p is None or not math.isfinite(p) or p < 0 for p in prices):
        raise ValueError(f"{model_name}: valid input/output prices are required before estimating or submitting.")
    estimate = config.estimate
    return n_calls * (estimate.assumed_input_tokens_per_call * prices[0] + estimate.assumed_output_tokens_per_call * prices[1]) / 1_000_000 * estimate.batch_discount


def build_new_batch_plans(results_dir, config, selected, questions_by_id, model_names, completed_manifest, limit_new_questions=None):
    batch_dir = results_dir.parent / "batches"
    completed_question_ids = question_ids_from_manifest(completed_manifest)
    historical_fingerprints = question_fingerprints_from_manifest(completed_manifest)
    historical = json.loads(completed_manifest.read_text()) if completed_manifest.exists() else {}
    from .prompts import VISIBLE_EXPLANATION_INSTRUCTION, SUGGESTED_ANSWER_TEMPLATE
    from .providers.openai_provider import build_request as openai_request
    from .providers.anthropic_provider import build_request as anthropic_request
    new_plans: dict[str, list] = {}
    for name in model_names:
        plan = build_plan(selected, questions_by_id, config, name)
        existing = load_existing_keys(results_dir / f"{name}.jsonl")
        builder = openai_request if name == "openai" else anthropic_request
        request = builder(getattr(config.models, name), "")
        settings = {k: v for k, v in request.items() if k not in ("input", "messages")}
        historical_compatible = (settings == historical.get("request_settings", {}).get(name)
                                 and VISIBLE_EXPLANATION_INSTRUCTION == historical.get("output_instruction")
                                 and SUGGESTED_ANSWER_TEMPLATE == historical.get("cue_template"))
        pending = pending_batch_keys(batch_dir, name)
        new_plan = [
            pc for pc in plan
            if pc.key not in existing
            and pc.key not in pending
            and not (historical_compatible and pc.question.source_question_id in completed_question_ids
                     and pc.question.fingerprint == historical_fingerprints.get(pc.question.source_question_id)
                     and pc.condition in historical.get("conditions", []) and pc.run_index in historical.get("run_indices", []))
        ]
        if limit_new_questions is not None:
            allowed_ids = []
            seen_ids = set()
            for pc in new_plan:
                qid = pc.question.question_id
                if qid not in seen_ids:
                    seen_ids.add(qid)
                    allowed_ids.append(qid)
                if len(allowed_ids) >= limit_new_questions:
                    break
            allowed = set(allowed_ids)
            new_plan = [pc for pc in new_plan if pc.question.question_id in allowed]
        new_plans[name] = new_plan
    return new_plans


