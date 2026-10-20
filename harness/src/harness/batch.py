"""Provider Batch API support for the CoT-faithfulness harness.

The batch path keeps the same PlannedCall objects and provider request builders
as the synchronous path. It changes only transport: requests are submitted as
an asynchronous provider batch and collected later.

OpenAI Batch uses a JSONL input file uploaded with purpose='batch'. Anthropic
Message Batches accepts the requests directly. Both providers expose results
keyed by the custom id, so the harness uses the existing resumable call key as
that id and can safely merge results into the normal raw JSONL files.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .providers.anthropic_provider import build_request as build_anthropic_request
from .providers.anthropic_provider import parse_anthropic_message
from .providers.openai_provider import build_request as build_openai_request
from .providers.openai_provider import parse_openai_response
from .providers.base import ProviderResult
from .runner import PlannedCall, append_result, load_existing_keys


TERMINAL_OPENAI_STATUSES = {"completed", "failed", "expired", "cancelled"}
TERMINAL_ANTHROPIC_STATUSES = {"ended", "canceled"}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _call_manifest(pc: PlannedCall, request_params: dict[str, Any]) -> dict[str, Any]:
    return {
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
        "request_params": request_params,
    }


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _record_from_result(
    pc_meta: dict[str, Any],
    result: ProviderResult,
    *,
    batch_id: str,
    batch_custom_id: str,
) -> dict[str, Any]:
    return {
        "key": pc_meta["key"],
        "question_id": pc_meta["question_id"],
        "source_question_id": pc_meta.get("source_question_id", pc_meta["question_id"]),
        "question_fingerprint": pc_meta.get("question_fingerprint"),
        "task": pc_meta["task"],
        "idx": pc_meta["idx"],
        "condition": pc_meta["condition"],
        "model_name": pc_meta["model_name"],
        "run_index": pc_meta["run_index"],
        "gold_letter": pc_meta["gold_letter"],
        "cued_letter": pc_meta["cued_letter"],
        "prompt": pc_meta["prompt"],
        "batch_id": batch_id,
        "batch_custom_id": batch_custom_id,
        "batch_collected_at": _utc_now(),
        **result.model_dump(),
    }


def build_openai_batch_jsonl(plan: Iterable[PlannedCall], model_cfg: Any) -> str:
    """Return the JSONL payload required by OpenAI's /v1/responses Batch API."""
    lines = []
    for pc in plan:
        lines.append(
            json.dumps(
                {
                    "custom_id": pc.key,
                    "method": "POST",
                    "url": "/v1/responses",
                    "body": build_openai_request(model_cfg, pc.prompt),
                },
                separators=(",", ":"),
            )
        )
    return "\n".join(lines) + ("\n" if lines else "")


def build_anthropic_batch_requests(plan: Iterable[PlannedCall], model_cfg: Any) -> list[dict[str, Any]]:
    """Return the requests payload required by Anthropic Message Batches."""
    return [
        {"custom_id": pc.key, "params": build_anthropic_request(model_cfg, pc.prompt)}
        for pc in plan
    ]


def pending_batch_keys(batch_dir: Path, provider: str) -> set[str]:
    """Return call keys already submitted to an uncollected batch.

    This prevents a second `batch-submit` from charging for duplicate requests
    while a previous batch is still processing (or has finished but has not yet
    been collected).
    """
    pending: set[str] = set()
    batch_dir = Path(batch_dir)
    if not batch_dir.exists():
        return pending
    failed_terminal = {"failed"}
    for path in sorted(batch_dir.glob(f"{provider}-*.json")):
        try:
            manifest = load_manifest(path)
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Cannot read batch reservation {path}; repair it before submitting.") from exc
        if manifest.get("collected_at"):
            continue
        if manifest.get("status") in failed_terminal:
            continue
        pending.update(c["key"] for c in manifest.get("calls", []))
    return pending


def _submission_intent(plan, model_cfg, batch_dir, results_path, provider, protocol_version):
    batch_dir = Path(batch_dir).resolve()
    batch_dir.mkdir(parents=True, exist_ok=True)
    path = batch_dir / f"{provider}-submission-{uuid.uuid4().hex}.json"
    builder = build_openai_request if provider == "openai" else build_anthropic_request
    manifest = {
        "schema_version": 2, "provider": provider, "model_name": provider,
        "model_id": model_cfg.model_id, "batch_id": None, "status": "submitting",
        "created_at": _utc_now(), "protocol_version": protocol_version,
        "results_path": str(Path(results_path).resolve()), "request_count": len(plan),
        "calls": [_call_manifest(pc, builder(model_cfg, pc.prompt)) for pc in plan],
        "manifest_path": str(path),
    }
    # Persist before contacting the provider. Unknown outcomes remain reserved.
    _write_manifest(path, manifest)
    return manifest


def submit_openai_batch(plan, model_cfg, *, batch_dir, results_path, protocol_version, client=None):
    if not plan:
        raise ValueError("Cannot submit an empty OpenAI batch")
    if client is None:
        from openai import OpenAI
        client = OpenAI()
    manifest = _submission_intent(plan, model_cfg, batch_dir, results_path, "openai", protocol_version)
    path = Path(manifest["manifest_path"])
    input_path = path.with_suffix(".jsonl")
    input_path.write_text(build_openai_batch_jsonl(plan, model_cfg), encoding="utf-8")
    manifest["input_path"] = str(input_path)
    _write_manifest(path, manifest)
    with input_path.open("rb") as fh:
        uploaded = client.files.create(file=fh, purpose="batch")
    manifest["input_file_id"] = uploaded.id
    _write_manifest(path, manifest)
    batch = client.batches.create(
        input_file_id=uploaded.id, endpoint="/v1/responses", completion_window="24h",
        metadata={"project": "xai-group7-cot-faithfulness", "protocol": protocol_version,
                  "model": model_cfg.model_id, "submission": path.stem},
    )
    manifest.update(batch_id=batch.id, status=getattr(batch, "status", "unknown"))
    _write_manifest(path, manifest)
    return manifest


def submit_anthropic_batch(plan, model_cfg, *, batch_dir, results_path, protocol_version, client=None):
    if not plan:
        raise ValueError("Cannot submit an empty Anthropic batch")
    if client is None:
        from anthropic import Anthropic
        client = Anthropic()
    manifest = _submission_intent(plan, model_cfg, batch_dir, results_path, "anthropic", protocol_version)
    batch = client.messages.batches.create(requests=build_anthropic_batch_requests(plan, model_cfg))
    manifest.update(batch_id=batch.id, status=getattr(batch, "processing_status", "unknown"))
    _write_manifest(Path(manifest["manifest_path"]), manifest)
    return manifest


def openai_batch_status(batch_id: str, *, client: Any | None = None) -> dict[str, Any]:
    if client is None:
        from openai import OpenAI

        client = OpenAI()
    return client.batches.retrieve(batch_id).model_dump()


def anthropic_batch_status(batch_id: str, *, client: Any | None = None) -> dict[str, Any]:
    if client is None:
        from anthropic import Anthropic

        client = Anthropic()
    return client.messages.batches.retrieve(batch_id).model_dump()


def _decode_openai_file_content(content: Any) -> str:
    if hasattr(content, "text") and isinstance(content.text, str):
        return content.text
    if hasattr(content, "read"):
        raw = content.read()
        if isinstance(raw, bytes):
            return raw.decode("utf-8")
        return str(raw)
    if isinstance(content, bytes):
        return content.decode("utf-8")
    return str(content)


def _reconcile(manifest, items, provider):
    """Require one terminal outcome per requested ID before releasing reservations."""
    calls = {c["key"]: c for c in manifest["calls"]}
    if len(calls) != len(manifest["calls"]):
        raise RuntimeError("Duplicate IDs in batch manifest")
    outcomes = {}
    for item in items:
        custom_id = item.get("custom_id")
        if custom_id not in calls or custom_id in outcomes:
            raise RuntimeError(f"Unknown or duplicate batch result ID: {custom_id}")
        outcomes[custom_id] = item
    results_path = Path(manifest["results_path"])
    existing = load_existing_keys(results_path)
    collected = skipped = 0
    failures = []
    for custom_id, item in outcomes.items():
        if custom_id in existing:
            skipped += 1
            continue
        if provider == "openai":
            response = item.get("response") or {}
            body = response.get("body") or {}
            success = (200 <= response.get("status_code", 0) < 300 and not item.get("error")
                       and not body.get("error") and body.get("status", "completed") == "completed")
            parser = parse_openai_response
        else:
            block = item.get("result") or {}
            body = block.get("message") or {}
            success = block.get("type") == "succeeded"
            parser = parse_anthropic_message
        if not success:
            failures.append(item)
            continue
        meta = calls[custom_id]
        answer, reasoning, visibility = parser(body)
        result = ProviderResult(
            requested_model=manifest["model_id"], api_model_id=body.get("model", manifest["model_id"]),
            request_params=meta["request_params"], timestamp=_utc_now(), raw_response=body,
            answer_text=answer, reasoning_text=reasoning, reasoning_visibility=visibility,
        )
        append_result(results_path, _record_from_result(meta, result, batch_id=manifest["batch_id"], batch_custom_id=custom_id))
        existing.add(custom_id)
        collected += 1
    missing = set(calls) - set(outcomes) - existing
    if failures:
        error_path = Path(manifest["manifest_path"]).with_suffix(".errors.jsonl")
        error_path.write_text("".join(json.dumps(x) + "\n" for x in failures), encoding="utf-8")
    manifest.update(collected_count=len(set(calls) & existing), failed_count=len(failures), missing_ids=sorted(missing))
    if not missing:
        manifest["collected_at"] = _utc_now()
    _write_manifest(Path(manifest["manifest_path"]), manifest)
    return {"status": manifest["status"], "collected": collected, "skipped": skipped,
            "failed": len(failures), "missing": len(missing)}


def collect_openai_batch(manifest, *, client=None):
    if client is None:
        from openai import OpenAI
        client = OpenAI()
    batch = client.batches.retrieve(manifest["batch_id"])
    manifest.update(status=batch.status, last_checked_at=_utc_now())
    _write_manifest(Path(manifest["manifest_path"]), manifest)
    if batch.status not in TERMINAL_OPENAI_STATUSES:
        return {"status": batch.status, "collected": 0, "skipped": 0, "failed": 0}
    items = []
    for name in ("output_file_id", "error_file_id"):
        file_id = getattr(batch, name, None)
        if file_id:
            manifest[name] = file_id
            content = _decode_openai_file_content(client.files.content(file_id))
            items.extend(json.loads(line) for line in content.splitlines() if line.strip())
    if batch.status == "failed" and not items:
        # Input validation failure means none of the requests was executed.
        items = [{"custom_id": c["key"], "error": {"code": "batch_validation_failed"}} for c in manifest["calls"]]
    return _reconcile(manifest, items, "openai")


def collect_anthropic_batch(manifest, *, client=None):
    if client is None:
        from anthropic import Anthropic
        client = Anthropic()
    batch = client.messages.batches.retrieve(manifest["batch_id"])
    manifest.update(status=batch.processing_status, last_checked_at=_utc_now())
    _write_manifest(Path(manifest["manifest_path"]), manifest)
    if batch.processing_status != "ended":
        return {"status": batch.processing_status, "collected": 0, "skipped": 0, "failed": 0}
    return _reconcile(manifest, [entry.model_dump() for entry in client.messages.batches.results(manifest["batch_id"])], "anthropic")
