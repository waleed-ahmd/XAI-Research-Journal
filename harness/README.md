# CoT explanation evaluation harness — Group 7

This harness compares original, suggested-wrong-answer cue, and original-repeat
responses from Claude Opus 5.5 and GPT-5.6 Sol. It rates short **visible
explanations**, not private chain-of-thought or API reasoning summaries. The
study is a controlled adaptation of the Suggested Answer experiment; answer
accuracy and stability alone do not prove explanation faithfulness.

## Protocols and project state

- `config.yaml`: original 30-question Temporal Sequences protocol.
- `config.extended.yaml`: optional 270-question exploratory extension: 30 Temporal
  Sequences questions and 20 from each of the other 12 released task types.
- Each question has three conditions and one run per model. Reusing 60 historical
  questions leaves 210 new questions: 630 new requests per provider, 1,260 total.
  Combined with the 360 historical responses, the target is 1,620 responses.
- Batch transport and recovery have offline regression tests. No real batch is
  submitted by setup, selection, estimation, historical import or tests. Provider
  acceptance and actual costs still need a small real smoke batch.

Questions come from the [released Turpin dataset](https://github.com/milesaturpin/cot-unfaithfulness/tree/main/data/bbh).
The correctly spelled task name is `causal_judgment`. Both models use the same
fixed selection. Historical cue letters are preserved; newly sampled questions
use deterministic wrong letters from the extension seed.

## Setup

Python 3.11 or later, from the repository root:

```sh
cd harness
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Keep your existing `harness/.env`, or copy `.env.example` if you have not created
one. The CLI loads it automatically without overriding exported variables. Never
commit API keys. Updating dependencies does not require deleting the environment.

## Recommended extension workflow

Run these commands from `harness/` with the virtual environment activated.

### 1. Fetch the public datasets (no model charges)

```sh
cot-harness --config config.extended.yaml fetch-data
```

### 2. Create and freeze the selection (offline)

```sh
cot-harness --config config.extended.yaml \
  --selected-path data/selected_questions_extended.json \
  --results-dir results/raw select-extended
```

The command preserves historical question content and fills the task quotas.
Selections contain content fingerprints so duplicate source `idx` values do not
resolve to the wrong question. A metadata sidecar records selection settings and
historical cue provenance. Both files belong together and should be committed.

Existing selections are never overwritten. If you generated an extension with
the earlier implementation, use a new filename: it did not persist fingerprints.
Do not change the frozen selection after submitting requests.

### 3. Estimate a small batch (offline)

```sh
cot-harness --config config.extended.yaml \
  --selected-path data/selected_questions_extended.json \
  --results-dir results/raw batch-estimate --limit-new-questions 20
```

The default historical manifest reserves 60 known questions only when their
fingerprints and recorded provider request settings match this protocol.
Completed and pending calls are excluded individually, so partial failures do
not suppress other conditions or the other model. A fresh smoke run plans 60
calls per provider, 120 total. A fresh full extension plans 630 per provider.

The configured 260 input / 500 output tokens are **planning assumptions**, not
measured bounds for the broader tasks. Missing or invalid pricing blocks paid
submission. `--openai-budget` and `--anthropic-budget` are optional limits on
**estimated spend**, not provider-side caps or guarantees. Output limits allow
more than 500 tokens; reasoning tokens can increase actual usage. Check current
provider pricing and use the smoke batch to calibrate before submitting the rest.
Do not rely on balances copied from an earlier conversation.

### 4. Submit the smoke batch (paid; asks for confirmation)

```sh
cot-harness --config config.extended.yaml \
  --selected-path data/selected_questions_extended.json \
  --results-dir results/raw batch-submit --limit-new-questions 20
```

Use `--model openai` or `--model anthropic` to run one provider. Use the budget
options with your own current estimated-spend limits if desired. `--yes` skips
confirmation and should be used only for an intentionally authorised run.

Each provider gets the existing request body through its Batch API. OpenAI
uses `/v1/responses`; Anthropic uses Message Batches. Results are matched by
unique `custom_id`, never by return order.

### 5. Check status and collect

```sh
cot-harness --config config.extended.yaml --results-dir results/raw batch-status
cot-harness --config config.extended.yaml --results-dir results/raw batch-collect
```

`batch-collect --batch-id ID` targets one provider batch. Collection is resumable:
responses already saved are not appended again. Successful partial results from
expired/cancelled OpenAI batches are retained. HTTP/provider errors are saved
separately and remain eligible for retry. Both output and error files are
reconciled against the submitted IDs; missing or duplicate outcomes do not
silently mark a batch collected.

After collecting the smoke run, inspect parse failures and usage and check both
provider balances. Adjust the planning assumptions if necessary, then estimate
and submit the remaining calls without `--limit-new-questions`. The planner
resubmits only missing, unreserved calls, not whole partially completed questions.

### 6. Import historical responses into a separate directory (offline)

From the repository root:

```sh
./harness/scripts/restore_historical_results.sh
```

The importer reads the two completed experiments from pinned Git commit
`b6a3407` and validates both providers before writing to
`harness/results/historical/`. It leaves `results/raw/` untouched, so it works
before or after new batches. Repeating the import is idempotent; conflicting
records fail instead of being overwritten. `--output-dir PATH` and `--commit SHA`
are available for deliberate recovery; the expected source has 180 responses
per provider. The importer needs local Git history, not network or API keys.

### 7. Analyse the combined dataset

From `harness/`:

```sh
cot-harness --config config.extended.yaml \
  --results-dir results/raw analyze \
  --historical-dir results/historical \
  --summary-dir results/extended-summary
```

Analysis excludes `dryrun_mock.jsonl`, deduplicates identical saved keys and
rejects conflicting or repeated response identities. Historical inputs remain
separate from live responses. Check completeness against the target 270 questions
and 1,620 responses before reporting a full-run result; partial analyses are not
full-run estimates. The historical and new cohorts should also be reported
separately because the task mix and collection protocols differ.

## Batch reservations and recovery

`results/batches/` stores the provider IDs, input payloads, errors, request metadata
and absolute destination paths. These are local run artifacts: preserve them
alongside the raw responses. Do not delete them to force a retry.

- A submission intent is saved atomically **before** contacting the provider.
- A process lock prevents overlapping local submit/status/collect operations.
- If the outcome is unknown (for example, a timeout after the provider accepted
  a batch), its keys stay reserved. Status/collect tell you to reconcile it.
  Check the provider dashboard/API and attach the confirmed `batch_id` to the
  corresponding manifest before collecting. If you establish that no batch was
  accepted, explicitly set that reservation to `failed` to release it. Never
  clear a reservation merely because a request timed out.
- Corrupt manifests block resubmission until repaired. Ended batches with missing
  result IDs stay reserved until reconciled; successfully saved calls are safe.
- A validation-failed OpenAI batch can be retried after correcting its input.
- Paths in manifests are absolute. If you move the checkout, update the recorded
  paths deliberately before collection. Keep one manifest directory for a run;
  copies on other machines are not coordinated by the local lock.

## Synchronous and mock commands

The existing `estimate`, `pilot`, `run`, `dry-run` and `analyze` commands remain.
`dry-run` is free and writes only synthetic responses. Paid synchronous runs use
ordinary call-key resumability; historical Batch reservations are **not** consulted
by synchronous `run`. Do not switch transports into the same run while batches
are pending or expect synchronous calls to reuse old historical keys.

## Analysis and human rating

Outputs include `metrics_summary.csv`, `needs_review.csv`, accuracy/flip charts,
a blinded coding sheet and its separate model key. Metrics contain counts,
denominators and Wilson 95% confidence intervals. The coding sheet includes only
answers that switch to the wrong suggested option. Two human raters should use
the [draft acknowledgement rubric](ACKNOWLEDGEMENT_RUBRIC.md); API reasoning
summaries must not substitute for visible explanations. Empty sheets mean there
were no cue flips, not completed human ratings.

## Reproducibility and compatibility

Call keys include protocol/model settings, the fixed selection and the exact
rendered prompt. Pricing and display labels do not invalidate keys. A question's
fingerprint is retained in its selection, saved response and Batch manifest;
new fingerprinted IDs prevent distinct source rows sharing `idx` from being
merged in analysis. Ambiguous legacy IDs are rejected rather than guessed.

Historical responses keep their original keys, IDs and request parameters. Their
explicit completed-question manifest records content, old cue letters and request
settings. Changing models or generation settings prevents reuse of incompatible
historical requests. Keep the original experiments intact for separate reporting.

## Tests

```sh
pytest tests -q
```

Tests use fixtures and fake clients only. They cover request formatting, real CLI
submission paths, per-call retries, duplicate IDs, failed/partial collection,
reservation recovery, historical imports and analysis deduplication.
