# XAI Research Journal — Group 7

We investigate whether modern models’ visible explanations acknowledge an
incorrect suggested answer when their final answer changes to that suggestion.
The project compares Claude Opus 5.5 and GPT-5.6 Sol using original, cued and
original-repeat prompts. It does not claim to expose private chain-of-thought or
prove explanation faithfulness from answer accuracy alone.

## Current state — 21 October 2026

Collection is complete: **1,620 saved responses**, with 810 per model. Each model
has 270 original, 270 cue and 270 original-repeat responses. The submitted batches
finished without failed or missing requests. Combined analysis outputs and human
ratings have not yet been produced.

## Main study: 270 questions across 13 BBH task types

The project has pivoted from an initial 30-question Temporal Sequences sample
to a broader, task-balanced study. The earlier experiments serve as pilots and
contribute their existing responses to the accumulated dataset.

| Stage | Unique questions | Model responses | State |
|---|---:|---:|---|
| Pilot 01 — Temporal Sequences | 30 | 180 | Completed |
| Pilot 02 — Logical Deduction, Date Understanding and Disambiguation QA | 30 | 180 | Completed |
| Main-study expansion — remaining task quotas | 210 | 1,260 | Collected |
| **Accumulated main study** | **270** | **1,620** | **Collection complete** |

The final selection contains 30 Temporal Sequences questions and 20 from each
of the other 12 released task types. Each question has three conditions and is
answered by both models: six responses per unique question. The models receive
the same fixed selection. Historical content and cue letters are preserved;
completed compatible calls are reused rather than charged again.

The motivation is broader evidence: the first pilot had perfect accuracy and
no cue flips; the second produced one GPT cue flip. Expanding the task coverage
allows us to examine whether that limited cue sensitivity holds across different
reasoning tasks. The pivot was informed by pilot outcomes and is documented in
the [20 October journal entry](Journal/2026-10-20.md). Report the pilot cohorts
and new questions separately as well as in the accumulated results, so the
change in scope remains transparent.

## Running and checking the study

`harness/config.extended.yaml` is the **main-study configuration**. Its filename
is retained for command compatibility. `harness/config.yaml` and the historical
selections retain the original pilot protocol for provenance.

See the [harness runbook](harness/README.md) for setup, frozen selection, estimated
costs, smoke batches, collection, recovery and combined analysis. Batch safeguards
include fingerprinted question identities, per-call resumability, durable
submission reservations and collection of successful partial batches. Tests use fake clients and do not incur API charges. Paid collection used a
20-question smoke batch followed by the remaining 190 new questions per model.
Budget options check estimated spend, not guaranteed charges.

The saved datasets are in [`harness/results/raw/`](harness/results/raw/)
(630 new responses per model) and
[`harness/results/historical/`](harness/results/historical/)
(180 pilot responses per model). The
[results guide](harness/results/README.md) explains the files and analysis command.
The [historical import script](harness/scripts/restore_historical_results.sh) can
recover the pilot data from pinned local Git history if needed.

## Project organisation

Experiment code, configuration, selections, tests and run outputs live under
`harness/`. Journal entries, literature notes, papers and assignment requirements
remain separate research material. The [architecture guide](harness/ARCHITECTURE.md)
describes the runtime layers and distinguishes raw data from derived reports.

## Research record

- [Research journal](journal/): dated decisions, pivots and contributions.
- [Literature notes](literature/): background and interpretation.
- [Human-rating rubric](harness/ACKNOWLEDGEMENT_RUBRIC.md): draft instructions for
  independent cue-acknowledgement rating of visible explanations.
- [Short-paper specification](spec/Xai-ShortPaper.md): report requirements.

Accuracy, cue-flip rates and baseline instability still need to be calculated
for the combined dataset. Human acknowledgement ratings require independent
review of the eligible visible explanations. Collection success does not imply
answer correctness.

## What the comparison measures

- **Original:** the question without a suggested answer.
- **Cue:** the same question plus a deterministic incorrect suggestion.
- **Original-repeat:** a separate call with the original prompt, to measure
  answer variation without the cue.

A switch to the cued answer is compared with variation between the two original
calls. Human raters then assess whether the visible explanation acknowledges the
suggestion. A single switch cannot establish its cause, and an explanation that
sounds correct does not establish that it describes the model’s internal reasoning.
