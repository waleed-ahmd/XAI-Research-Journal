# Journal Entry — 2026-10-07

*Written on 2026-10-09, after the fact — I opened the PR with these changes
on 2026-10-07 but forgot to log the entry the same day. Dating this to when
the work actually happened rather than when I'm writing it up.*

**Entry type:** Decision
**Author:** Luca Knierim

## What happened

Built the experiment harness (`harness/`) that the group's 30-question BBH
re-evaluation of Turpin et al. actually runs on: loading the real BBH
questions, building the cue/prompt logic, talking to Anthropic/OpenAI (plus a
free mock for testing), running resumably, and turning raw answers into the
metrics/coding sheet the paper needs. Opened as a PR rather than merged
straight to `main`, with 46 automated tests, no real model calls made while
building it.

## Decisions made

- **Decision:** Load questions from Turpin et al.'s own released data
  (github.com/milesaturpin/cot-unfaithfulness, MIT licensed) instead of
  writing our own.
  - **Why:** Our question is specifically whether their finding still holds
    on current models — using their exact questions and wording keeps that
    comparison honest, rather than us accidentally testing something subtly
    different.

- **Decision:** Pick the wrong-answer cue ourselves, deterministically from
  our own seed, rather than trusting the `random_ans_idx` field already in
  Turpin's data files.
  - **Why:** Checked that field against the real data and it isn't reliably
    guaranteed to point at a wrong answer for every question. A cue that
    sometimes points at the correct answer would silently break the whole
    point of the test, so we compute and verify it ourselves (with a test
    checking this across every loaded question) instead of assuming.

- **Decision:** Use three "providers" — real Anthropic, real OpenAI, and a
  deterministic mock that never touches the network — and test everything
  against the mock only.
  - **Why:** Lets the whole pipeline (question selection, prompts, running,
    analysis) get built and checked for free, with real providers only
    switched on once we're actually ready to spend money, and only after an
    explicit confirmation step.

- **Decision:** Record how much of each model's reasoning we can actually
  see (`reasoning_visibility`: full / summary / none) on every saved answer,
  rather than assuming we can see all of it.
  - **Why:** Checked both providers' current docs — neither ever returns the
    literal chain of thought, only an optional written summary or nothing.
    This caps what the study can honestly claim, so it needs to be recorded
    per answer, not assumed.

- **Decision:** Leave the OpenAI model id blank in config rather than
  guessing one.
  - **Why:** The plan named "GPT-5.6 Luna," but that model doesn't exist
    under that name in OpenAI's current docs. Left blank on purpose so a
    real run fails loudly instead of silently calling the wrong model.
    (Resolved in a later entry/PR once the group confirmed the actual
    model.)

- **Decision:** Cue acknowledgement is rated by two humans on a shuffled,
  model-name-hidden sheet, with Cohen's kappa for agreement — not by asking
  another model to judge it.
  - **Why:** Judging whether an explanation *admits* the cue influenced it
    is exactly the kind of subjective call that shouldn't be delegated to
    an AI when the AI's own faithfulness is what's being studied.

## Pivots, dead ends, disagreements

- Turpin's `val_data.json` files turned out to be wrapped in
  `{"canary": ..., "data": [...]}` rather than being a bare list, and 3 of
  the 13 BBH tasks have rows with no `idx` field at all — both broke my
  first pass at the data loader and had to be handled explicitly.
- Their repo also contains two slightly different "Suggested Answer" cue
  sentences in different files; only one of them is actually wired into the
  prompt-building code the other is dead code in an unused ablation loop.
  Had to trace their actual source to confirm which one is real before
  copying the wording.

## Still open

- [ ] OpenAI model id was still unconfirmed at the time this PR went up.

## Who did what

Built solo, with AI pair-programming assistance for the implementation.

## Feeds into the report

- **Report section:** Methodology
- **What from this entry lands there:** Data source and licensing, prompt/cue
  construction, the reasoning-visibility caveat on what the study can claim,
  and the human-rating setup for cue acknowledgement.

---

**Next checkpoint:** Confirm the OpenAI model id and run the pilot.
