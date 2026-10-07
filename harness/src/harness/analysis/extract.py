"""Parses the final multiple-choice answer out of a model's response text.

Anything ambiguous or unparseable returns None so the caller can route it
to needs_review.csv — we never guess an answer letter.
"""

from __future__ import annotations

import re

# Matches "... is: (B)", "...is:\n(b)", with or without a space after the colon.
_ANSWER_RE = re.compile(r"is:\s*\(\s*([A-Za-z])\s*\)")


def extract_answer(answer_text: str) -> str | None:
    matches = _ANSWER_RE.findall(answer_text)
    if not matches:
        return None
    letters = {m.upper() for m in matches}
    if len(letters) > 1:
        # The response asserts more than one distinct final answer — ambiguous.
        return None
    return letters.pop()
