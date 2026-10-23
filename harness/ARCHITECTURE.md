# Harness architecture and project boundaries

The experiment implementation is contained in `harness/`. Research notes,
readings and assignment specifications remain outside the executable package.
No runtime command imports or writes to those research folders.

```text
repository/
├── README.md                   project scope and entry points
├── journal/                    dated research notes, including the pivot entry
├── literature/                 reading notes
├── papers/                     reference papers
├── spec/                       assignment requirements
└── harness/
    ├── config*.yaml            protocols and generation settings
    ├── data/                   frozen selections and historical identities
    │   └── bbh/                downloaded benchmark cache (ignored)
    ├── src/harness/            installable Python package
    ├── tests/                  offline fixtures and regression tests
    ├── scripts/                local recovery entry points
    └── results/                runtime data, manifests and analysis
```

## Runtime layers

| Module | Responsibility |
|---|---|
| `cli.py` | Parse arguments, request paid-run confirmation, invoke services and print status |
| `config.py`, `data/` | Validate settings, load benchmark rows and freeze exact content identities |
| `prompts.py`, `cue.py` | Construct the controlled prompts and deterministic incorrect suggestions |
| `runner.py` | Build keyed call plans and execute resumable synchronous calls |
| `batch_planning.py` | Plan only missing/unreserved calls and estimate costs without provider contact |
| `batch.py`, `providers/` | Provider request formatting, submission, collection and parsing |
| `historical.py` | Recover validated historical responses from pinned local Git history |
| `analysis/records.py` | Reconcile saved records, reject conflicts and normalise content identities for analysis |
| Other `analysis/` modules | Compute metrics, create figures and prepare blinded human-rating material |

Batch and synchronous transport share request builders and prompt construction.
The synchronous path does not consult Batch reservations, so use the documented
Batch workflow consistently for the main study. Keep the same frozen selection
and manifest directory throughout collection.

## Data separation

- **Protocols and selections:** tracked configuration, question IDs, fingerprints
  and selection metadata. They are evidence of what was planned, not responses.
- **Raw responses:** `results/raw/`, appended during collection; do not edit these
  to change metrics or combine them manually with historical datasets.
- **Historical responses:** `results/historical/`, imported separately and retained
  with their original request settings and keys.
- **Submission state:** `results/batches/`, including reservations and errors.
  Back up these files with the raw data so interrupted runs can be reconciled.
- **Derived outputs:** use `results/summary/` for main-study CSVs, charts
  and coding sheets. They can be regenerated from saved responses.
- **Human coding:** keep blinded sheets separate from their model-identity keys.
  The final ratings should be preserved rather than overwritten by re-analysis.

Only combine raw and historical inputs through `analyze --historical-dir`.
Analysis recognises exact content across old and fingerprinted IDs, rejects
repeated observations and never changes the original JSONL files.

See [the runbook](README.md) for commands and [the results guide](results/README.md)
for output locations. The only required secret file is the ignored `.env` in
`harness/`; API keys never belong in selections, reports or source control.
