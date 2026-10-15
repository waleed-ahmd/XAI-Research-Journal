"""Shared CSV-writing helper for the analysis outputs."""

from __future__ import annotations

import csv
from pathlib import Path


def write_dict_csv(rows: list[dict], out_path: Path, fieldnames: list[str]) -> None:
    """Writes `rows` to `out_path` as CSV with header `fieldnames`.

    Extra keys in a row beyond `fieldnames` are ignored; missing keys are
    written as blank, matching `csv.DictWriter`'s own behaviour.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
