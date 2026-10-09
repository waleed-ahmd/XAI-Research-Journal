"""Downloads BBH val_data.json files from Turpin et al.'s released repo.

Source: https://github.com/milesaturpin/cot-unfaithfulness (MIT licence).
This only fetches their published data/prompt files — it makes no model
API calls and costs nothing.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

REPO_RAW_BASE = (
    "https://raw.githubusercontent.com/milesaturpin/cot-unfaithfulness/main"
)


def fetch_task_data(task: str, data_dir: Path, *, force: bool = False) -> Path:
    out_path = Path(data_dir) / task / "val_data.json"
    if out_path.exists() and not force:
        return out_path
    url = f"{REPO_RAW_BASE}/data/bbh/{task}/val_data.json"
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 - fixed https host
        raw = json.load(resp)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(raw, f)
    return out_path


def fetch_all(tasks: list[str], data_dir: Path, *, force: bool = False) -> None:
    for task in tasks:
        fetch_task_data(task, data_dir, force=force)
