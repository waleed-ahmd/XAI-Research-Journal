"""Shared JSONL file reading, used by both the runner (resumability) and the
CLI's `analyze` command.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path


def read_jsonl(path: Path) -> Iterator[dict]:
    """Yields each non-blank line of `path` parsed as JSON. Nothing if `path` doesn't exist."""
    path = Path(path)
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)
