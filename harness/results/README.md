# Experiment results

Collection finished on **21 October 2026**. There are **1,620 saved responses**:
270 questions × three conditions × two models. Each provider has 810 responses,
with 270 each for `original`, `cue` and `original_repeat`. The Batch collections
reported no failed or missing requests. This describes collection completeness,
not answer accuracy.

## Saved data

| File | Responses | Contents |
|---|---:|---|
| [raw/anthropic.jsonl](raw/anthropic.jsonl) | 630 | New Claude responses for 210 questions |
| [raw/openai.jsonl](raw/openai.jsonl) | 630 | New OpenAI responses for the same questions |
| [historical/anthropic.jsonl](historical/anthropic.jsonl) | 180 | Claude responses for the 60 pilot questions |
| [historical/openai.jsonl](historical/openai.jsonl) | 180 | OpenAI responses for the same pilot questions |

Each JSONL line is one response record. It contains the question identity,
condition, prompt, gold and cued answer letters, visible answer text, model and
request settings, and the provider response with usage metadata. Reasoning
summaries, when returned, are distinct from the visible explanations being rated.

The frozen selection and its metadata live in `../data/selected_questions_extended.json` and the
adjacent `.metadata.json` file. `../data/completed_question_ids.json` records
historical content fingerprints, cue letters and request settings.

## Supporting files

- `batches/`: provider batch IDs, submitted calls, OpenAI input JSONL payloads,
  collection state and any errors used to reconcile submissions with responses.
- `summary/`: combined metrics, charts and rating sheets generated
  from the saved responses.

## Generate the combined analysis

From `harness/`, with the virtual environment activated:

```sh
cot-harness --config config.extended.yaml --results-dir results/raw analyze \
  --historical-dir results/historical --summary-dir results/summary
```

This creates `metrics_summary.csv`, `needs_review.csv`, `accuracy.png`,
`flip_rates.png`, `coding_sheet.csv` and
`coding_sheet_KEY_do_not_share_with_raters.csv`. Keep the model-identity key
separate from the sheets supplied to human raters. Metrics and charts do not
complete the human acknowledgement ratings.

Report historical and new cohorts separately as well as together: pilot outcomes
informed the expanded selection. Do not treat repeated conditions as independent
questions or interpret accuracy alone as proof of explanation faithfulness.

## Recover historical responses

The historical files are already present. If they are lost, run this from the
repository root with the pinned Git history available:

```sh
./harness/scripts/restore_historical_results.sh
```

The importer validates the source data, rejects conflicts and leaves `raw/`
untouched. Repeated imports do not duplicate responses. See the
[harness runbook](../README.md) for setup and Batch recovery.
