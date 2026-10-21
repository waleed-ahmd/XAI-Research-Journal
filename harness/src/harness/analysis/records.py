"""Read and reconcile experiment responses before computing metrics.

Historical IDs may omit fingerprints. Recover content identities from original
prompts so a new ID cannot cause the same response/question to be counted twice.
"""
from __future__ import annotations

from pathlib import Path

from ..data.models import fingerprint_text
from ..jsonl import read_jsonl
from ..prompts import VISIBLE_EXPLANATION_INSTRUCTION


def load_analysis_records(directories: list[Path]) -> list[dict]:
    keyed = {}
    fingerprints = {}
    suffix = "\n\n" + VISIBLE_EXPLANATION_INSTRUCTION
    for directory in directories:
        for path in sorted(directory.glob("*.jsonl")):
            if path.name == "dryrun_mock.jsonl":
                continue
            for record in read_jsonl(path):
                key = record.get("key", (record["model_name"], record["question_id"], record["condition"], record["run_index"]))
                if key in keyed and keyed[key] != record:
                    raise ValueError(f"Conflicting saved response key in {path}")
                keyed[key] = record
                fingerprint = record.get("question_fingerprint")
                prompt = record.get("prompt", "")
                if not fingerprint and record["condition"] == "original" and prompt.endswith(suffix):
                    fingerprint = fingerprint_text(prompt[:-len(suffix)])
                if fingerprint:
                    group = (record["model_name"], record["question_id"])
                    if group in fingerprints and fingerprints[group] != fingerprint:
                        raise ValueError(f"Conflicting question content for {group}")
                    fingerprints[group] = fingerprint
    identities = set()
    records = []
    for record in keyed.values():
        fingerprint = fingerprints.get((record["model_name"], record["question_id"]))
        source_id = record.get("source_question_id") or ":".join(record["question_id"].split(":")[:2])
        content_id = f"{source_id.split(':')[0]}:{fingerprint}" if fingerprint else record["question_id"]
        identity = (record["model_name"], content_id, record["condition"], record["run_index"])
        if identity in identities:
            raise ValueError(f"Duplicate response identity: {identity}")
        identities.add(identity)
        # Normalise only the analysis view; saved raw records are never modified.
        records.append({**record, "question_id": content_id})
    return records
