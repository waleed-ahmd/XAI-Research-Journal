"""Parses the final multiple-choice answer out of a model's response text.

Anything ambiguous or unparseable returns None so the caller can route it
to needs_review.csv — we never guess an answer letter.
"""

from __future__ import annotations

import re

# One shared marker definition keeps parsing and blinded-text removal consistent.
_ANSWER_MARKER_RE = re.compile(
    r"\bThe\s+best\s+answer\s+is\s*:\s*\(\s*([A-Za-z])\s*\)",
    re.IGNORECASE,
)


def extract_answer(answer_text: str) -> str | None:
    matches = _ANSWER_MARKER_RE.findall(answer_text)
    if not matches:
        return None
    letters = {m.upper() for m in matches}
    if len(letters) > 1:
        # The response asserts more than one distinct final answer — ambiguous.
        return None
    return letters.pop()


def extract_visible_explanation(answer_text: str) -> str:
    """Return the user-visible explanation preceding the final answer marker.

    The API reasoning/"thinking" summary is deliberately not used for the
    faithfulness rating. This function extracts the explanation that the user
    actually sees from the provider's ordinary answer text.

    If the answer marker is absent, the full visible response is returned so
    that an unparseable response can still be inspected manually.
    """
    matches = list(_ANSWER_MARKER_RE.finditer(answer_text))
    if not matches:
        return answer_text.strip()
    return answer_text[: matches[0].start()].strip()
