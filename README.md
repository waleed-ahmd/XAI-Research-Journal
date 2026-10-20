# XAI Research Journal — Group 7

We investigate whether modern models’ visible explanations acknowledge an
incorrect suggested answer when their final answer changes to that suggestion.
The project compares Claude Opus 5.5 and GPT-5.6 Sol using original, cued and
original-repeat prompts. It does not claim to expose private chain-of-thought or
prove explanation faithfulness from answer accuracy alone.

## Main study: 270 questions across 13 BBH task types

The project has pivoted from an initial 30-question Temporal Sequences sample
to a broader, task-balanced study. The earlier experiments serve as pilots and
contribute their existing responses to the accumulated dataset.

| Stage | Unique questions | Model responses | State |
|---|---:|---:|---|
| Pilot 01 — Temporal Sequences | 30 | 180 | Completed |
| Pilot 02 — Logical Deduction, Date Understanding and Disambiguation QA | 30 | 180 | Completed |
| Main-study expansion — remaining task quotas | 210 | 1,260 | Planned; Batch workflow verified offline |
| **Accumulated main-study target** | **270** | **1,620** | **60 questions completed; 210 to collect** |

The final selection contains 30 Temporal Sequences questions and 20 from each
of the other 12 released task types. Each question has three conditions and is
answered by both models: six responses per unique question. The models receive
the same fixed selection. Historical content and cue letters are preserved;
completed compatible calls are reused rather than charged again.

The motivation is broader evidence: the first pilot had perfect accuracy and
no cue flips; the second produced one GPT cue flip. Expanding the task coverage
allows us to examine whether that limited cue sensitivity holds across different
reasoning tasks. The pivot was informed by pilot outcomes and is documented in
the [20 October journal entry](journal/2026-10-20.md). Report the pilot cohorts
and new questions separately as well as in the accumulated results, so the
change in scope remains transparent.

## Running and checking the study

`harness/config.extended.yaml` is the **main-study configuration**. Its filename
is retained for command compatibility. `harness/config.yaml` and the historical
selections retain the original pilot protocol for provenance.

See the [harness runbook](harness/README.md) for setup, frozen selection, estimated
costs, smoke batches, collection, recovery and combined analysis. Batch safeguards
include fingerprinted question identities, per-call resumability, durable
submission reservations and collection of successful partial batches. Tests and
full-pipeline verification use fake clients; the new paid collection has not yet
been submitted. Budget options check estimated spend, not guaranteed charges.

Use [the historical import script](harness/scripts/restore_historical_results.sh)
to recover the existing 360 responses into a separate local directory. The
[results guide](harness/results/README.md) describes the live, historical and
analysis outputs. Raw data and Batch manifests should be backed up locally.

## Research record

- [Research journal](journal/): dated decisions, pivots and contributions.
- [Literature notes](literature/): background and interpretation.
- [Human-rating rubric](harness/ACKNOWLEDGEMENT_RUBRIC.md): draft instructions for
  independent cue-acknowledgement rating of visible explanations.
- [Short-paper specification](spec/Xai-ShortPaper.md): report requirements.

Final accuracy, cue-flip rates, baseline instability and human acknowledgement
ratings for the 270-question study remain to be established after collection.
