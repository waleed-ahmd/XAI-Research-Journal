# Main-study results and local run state

Keep the two historical experiments separate from new Batch responses. Raw
responses and Batch manifests are local, gitignored artifacts; preserve backups
because stochastic model answers cannot be reproduced exactly by rerunning them.

| Directory | Purpose |
|---|---|
| `raw/` | Newly collected model responses |
| `historical/` | Imported historical responses, 180 per provider |
| `batches/` | Submission reservations, provider IDs, payloads and errors |
| `extended-summary/` | Suggested location for combined main-study analysis |

The main study targets 270 accumulated questions and 1,620 responses. Its
historical 60 pilot questions produced 360 responses: 180 from Experiment 01
(Temporal Sequences) and 180 from Experiment 02 (three task types). The exact
content fingerprints, old cue letters and generation settings are recorded in
`harness/data/completed_question_ids.json`.

From the repository root, restore the historical data from pinned local Git
history without touching live raw responses:

```sh
./harness/scripts/restore_historical_results.sh
```

The import is idempotent and rejects conflicting records. Then, from `harness/`:

```sh
cot-harness --config config.extended.yaml --results-dir results/raw analyze \
  --historical-dir results/historical --summary-dir results/extended-summary
```

The complete target is 270 questions and 1,620 responses. Analyse partial runs
as partial runs, and report the historical and new cohorts separately as well.
The [harness runbook](../README.md) explains selection, estimated-spend checks,
smoke batches, status, collection and recovery after ambiguous submissions.
