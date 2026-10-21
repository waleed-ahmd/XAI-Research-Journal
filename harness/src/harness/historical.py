"""Offline import of historical response records from a pinned Git revision."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .jsonl import read_jsonl


def import_historical(repo: Path, output_dir: Path, commit: str = "b6a3407") -> dict[str, int]:
    """Validate both providers before writing; repeated imports are idempotent."""
    if output_dir.resolve().name == "raw":
        raise ValueError("Use a separate historical directory, not the live raw directory")
    prepared = {}
    for provider in ("anthropic", "openai"):
        rows = []
        for experiment in ("experiment-01-temporal-sequences-pilot", "experiment-02-multitask-cue-followup"):
            path = f"harness/results/{experiment}/{provider}.jsonl"
            result = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=repo, check=True, capture_output=True, text=True)
            part = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
            if len(part) != 90 or any(r["model_name"] != provider for r in part):
                raise ValueError(f"Unexpected historical dataset: {path}")
            rows.extend(part)
        target = output_dir / f"{provider}.jsonl"
        merged = {}
        for record in [*read_jsonl(target), *rows]:
            key = record["key"]
            if key in merged and merged[key] != record:
                raise ValueError(f"Conflicting response for key {key}")
            merged[key] = record
        if len({(r['question_id'], r['condition'], r['run_index']) for r in rows}) != 180:
            raise ValueError("Historical response identities are not unique")
        prepared[target] = list(merged.values())
    output_dir.mkdir(parents=True, exist_ok=True)
    for target, rows in prepared.items():
        temp = target.with_suffix(".jsonl.tmp")
        temp.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
        os.replace(temp, target)
    return {p.stem: len(rows) for p, rows in prepared.items()}


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parents[2] / "results/historical")
    parser.add_argument("--commit", default="b6a3407")
    args = parser.parse_args()
    for provider, count in import_historical(args.repo, args.output_dir, args.commit).items():
        print(f"{provider}: {count} saved responses in {args.output_dir}")


if __name__ == "__main__":
    main()
