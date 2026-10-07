"""Data models for a single BBH question, as loaded from Turpin et al.'s
val_data.json files (github.com/milesaturpin/cot-unfaithfulness)."""

from __future__ import annotations

from string import ascii_uppercase

from pydantic import BaseModel, model_validator


class Question(BaseModel):
    task: str
    idx: int
    parsed_inputs: str
    multiple_choice_targets: list[str]
    multiple_choice_scores: list[float]

    @model_validator(mode="after")
    def _check_shapes(self) -> "Question":
        if len(self.multiple_choice_targets) != len(self.multiple_choice_scores):
            raise ValueError(
                f"{self.task}:{self.idx} has mismatched targets/scores lengths"
            )
        if sum(1 for s in self.multiple_choice_scores if s == max(self.multiple_choice_scores)) != 1:
            raise ValueError(
                f"{self.task}:{self.idx} does not have exactly one top-scoring answer"
            )
        return self

    @property
    def question_id(self) -> str:
        return f"{self.task}:{self.idx}"

    @property
    def num_choices(self) -> int:
        return len(self.multiple_choice_targets)

    @property
    def gold_index(self) -> int:
        best = max(self.multiple_choice_scores)
        return self.multiple_choice_scores.index(best)

    @property
    def gold_letter(self) -> str:
        return ascii_uppercase[self.gold_index]


class SelectedQuestion(BaseModel):
    """One question from the fixed, seeded 30-question (or pilot) set."""

    index: int
    task: str
    idx: int
    num_choices: int
    gold_letter: str
    cued_letter: str
