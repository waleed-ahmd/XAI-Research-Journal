"""Deterministic selection of the "Suggested Answer" cue letter.

The cue must always point at an *incorrect* option (see
harness/README.md and the project brief's hard rules), chosen
reproducibly from the study seed rather than at call time, so the same
question always gets the same cue across runs/resumes.
"""

from __future__ import annotations

import random
from string import ascii_uppercase


def choose_cue_letter(task: str, idx: int, gold_letter: str, num_choices: int, seed: int) -> str:
    if num_choices < 2:
        raise ValueError(f"{task}:{idx} has fewer than 2 choices; cannot pick a wrong cue")
    letters = list(ascii_uppercase[:num_choices])
    if gold_letter not in letters:
        raise ValueError(f"{task}:{idx} gold_letter {gold_letter!r} not in {letters}")
    letters.remove(gold_letter)
    rng = random.Random(f"{seed}:{task}:{idx}")
    return rng.choice(letters)
