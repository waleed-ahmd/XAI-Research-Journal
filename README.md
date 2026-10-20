# XAI Research Journal — Group 7

Research journal and experimental harness for studying whether visible model
explanations acknowledge incorrect suggested answers. The harness compares
original, cued and repeat responses while preserving raw provider results and
request settings.

See [harness documentation](harness/README.md) for setup, the original focused
protocol, the balanced all-task extension, free mock runs, cost estimates,
provider Batch APIs and analysis. [The rating rubric](harness/ACKNOWLEDGEMENT_RUBRIC.md)
describes human cue-acknowledgement coding. Research notes live in [journal](journal/)
and [literature](literature/).

The original study is a focused 30-question Temporal Sequences re-evaluation.
The optional `harness/config.extended.yaml` defines a separate 270-question
balanced extension across the 13 BBH task types used by Turpin et al. It reuses
the 60 questions already completed by the group and selects only the missing
questions for new paid calls.

Experiment datasets, raw model responses and analysis artifacts are kept out of
the normal code-review path. Historical question IDs are committed so the
extended selection can avoid duplicate paid runs. The study does not claim to
expose private chain-of-thought or prove explanation faithfulness.


Batch extension safeguards include fingerprinted question identities, per-model
and per-condition resumability, durable submission reservations, and collection
of successful partial batches. The implementation is verified offline with fake
clients; a small paid smoke batch is the next operational check, not something
setup or tests submit automatically.

Historical responses can be imported without overwriting new data using
`harness/scripts/restore_historical_results.sh`. Combined analysis uses
`analyze --historical-dir ... --summary-dir ...`; see the
[harness runbook](harness/README.md) for the exact steps. Budget options limit
estimated spend only and are not guarantees of actual charges.
