"""CLI entry point: `cot-harness <command>`.

Hard rule: no paid API call happens without the estimate being shown and
the caller explicitly confirming (--yes, or an interactive y/N prompt).
`dry-run` is always free: it only ever talks to the mock provider.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
import json
from functools import wraps

import click
from dotenv import load_dotenv

from .config import DEFAULT_CONFIG_PATH, HarnessConfig, load_config
from .data.loader import load_all_questions, question_index
from .data.selection import (
    load_selected_questions,
    validate_saved_selection,
    selection_settings,
    select_questions,
    select_questions_balanced,
    question_ids_from_results,
    question_fingerprints_from_results,
    question_ids_from_manifest,
    question_fingerprints_from_manifest,
    write_selected_questions,
)
from .providers.mock import MockProvider
from .runner import build_plan, load_existing_keys, run_plan
from .batch import (
    anthropic_batch_status,
    collect_anthropic_batch,
    collect_openai_batch,
    load_manifest,
    openai_batch_status,
    pending_batch_keys,
    submit_anthropic_batch,
    submit_openai_batch,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = ROOT / "data" / "bbh"
DEFAULT_SELECTED_PATH = ROOT / "data" / "selected_questions.json"
DEFAULT_RESULTS_DIR = ROOT / "results" / "raw"
DEFAULT_SUMMARY_DIR = ROOT / "results" / "summary"


def _questions_by_id(config: HarnessConfig, data_dir: Path) -> dict:
    questions = load_all_questions(config.questions.tasks, data_dir)
    return question_index(questions)


def _get_or_select_questions(config: HarnessConfig, data_dir: Path, selected_path: Path):
    if selected_path.exists():
        selected = load_selected_questions(selected_path)
        try:
            validate_saved_selection(selected, config, data_dir, selected_path)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        return selected
    if config.questions.counts_by_task is not None:
        raise click.ClickException(
            "This config requires a balanced fixed selection. Run `select-extended` first "
            "with a dedicated --selected-path."
        )
    selected = select_questions(config, data_dir)
    write_selected_questions(selected, selected_path)
    import json
    Path(str(selected_path) + ".metadata.json").write_text(
        json.dumps(selection_settings(config), indent=2) + "\n"
    )
    click.echo(f"Wrote {len(selected)} selected questions to {selected_path}")
    return selected


def _estimate_cost(config: HarnessConfig, n_calls_per_model: int, *, batch: bool = False) -> str:
    lines = []
    for model_key, model_cfg in (
        ("anthropic", config.models.anthropic),
        ("openai", config.models.openai),
    ):
        in_price = model_cfg.price_per_million_input_tokens
        out_price = model_cfg.price_per_million_output_tokens
        if in_price is None or out_price is None or not model_cfg.model_id:
            lines.append(
                f"  {model_key} ({model_cfg.display_name}): cost UNKNOWN — "
                "model_id and/or pricing not confirmed in config.yaml yet"
            )
            continue
        in_tok = config.estimate.assumed_input_tokens_per_call * n_calls_per_model
        out_tok = config.estimate.assumed_output_tokens_per_call * n_calls_per_model
        cost = (in_tok / 1_000_000) * in_price + (out_tok / 1_000_000) * out_price
        if batch:
            cost *= config.estimate.batch_discount
        lines.append(
            f"  {model_key} ({model_cfg.display_name}, {model_cfg.model_id}): "
            f"{n_calls_per_model} calls, ~${cost:.2f} "
            f"(assumes {config.estimate.assumed_input_tokens_per_call} in [measured from "
            f"real prompts] / {config.estimate.assumed_output_tokens_per_call} out "
            f"[unmeasured guess] tokens/call — see harness/config.yaml)"
        )
    return "\n".join(lines)


@click.group()
@click.option("--config", "config_path", type=click.Path(path_type=Path), default=DEFAULT_CONFIG_PATH)
@click.option("--data-dir", type=click.Path(path_type=Path), default=DEFAULT_DATA_DIR)
@click.option("--selected-path", type=click.Path(path_type=Path), default=DEFAULT_SELECTED_PATH)
@click.option("--results-dir", type=click.Path(path_type=Path), default=DEFAULT_RESULTS_DIR)
@click.pass_context
def main(ctx, config_path, data_dir, selected_path, results_dir):
    # Loads ANTHROPIC_API_KEY/OPENAI_API_KEY from harness/.env into the process
    # environment, if that file exists. Never overrides a key already exported
    # in the real shell environment (python-dotenv's default). The SDKs read
    # these from os.environ themselves; this just makes `.env` actually work,
    # since nothing else in the codebase loads it. No-op if `.env` is absent
    # (e.g. for `dry-run`, which never needs real keys).
    load_dotenv(ROOT / ".env")
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config_path)
    ctx.obj["data_dir"] = data_dir
    ctx.obj["selected_path"] = selected_path
    ctx.obj["results_dir"] = results_dir


@main.command("fetch-data")
@click.pass_context
def fetch_data(ctx):
    """Downloads BBH val_data.json files from the Turpin et al. repo. No API cost."""
    from .data.fetch import fetch_all

    config: HarnessConfig = ctx.obj["config"]
    fetch_all(config.questions.tasks, ctx.obj["data_dir"])
    click.echo(f"Fetched data for tasks: {', '.join(config.questions.tasks)}")


@main.command("select-extended")
@click.option("--completed-manifest", type=click.Path(path_type=Path), default=ROOT / "data" / "completed_question_ids.json")
@click.pass_context
def select_extended(ctx, completed_manifest):
    """Create the balanced 270-question extension without duplicating the 60 completed items."""
    config: HarnessConfig = ctx.obj["config"]
    if config.questions.counts_by_task is None:
        raise click.ClickException("select-extended requires questions.counts_by_task in the config")
    selected_path = ctx.obj["selected_path"]
    if selected_path.exists():
        raise click.ClickException(
            f"{selected_path} already exists. Choose a new --selected-path; existing selections are never overwritten."
        )
    existing = question_ids_from_results(ctx.obj["results_dir"])
    existing |= question_ids_from_manifest(completed_manifest)
    fingerprints = question_fingerprints_from_results(ctx.obj["results_dir"])
    fingerprints.update(question_fingerprints_from_manifest(completed_manifest))
    historical_questions = json.loads(completed_manifest.read_text()).get("questions", {}) if completed_manifest.exists() else {}
    historical_cues = {qid: row["cued_letter"] for qid, row in historical_questions.items() if row.get("cued_letter")}
    try:
        selected = select_questions_balanced(
            config, ctx.obj["data_dir"], existing_question_ids=existing,
            existing_question_fingerprints=fingerprints,
            existing_question_cues=historical_cues,
        )
    except (ValueError, FileNotFoundError) as exc:
        raise click.ClickException(str(exc)) from exc
    write_selected_questions(selected, selected_path)
    Path(str(selected_path) + ".metadata.json").write_text(
        json.dumps({**selection_settings(config), "historical_questions": historical_questions}, indent=2) + "\n", encoding="utf-8"
    )
    from collections import Counter
    counts = Counter(s.task for s in selected)
    preserved = sum(1 for s in selected if f"{s.task}:{s.idx}" in existing)
    click.echo(f"Wrote {len(selected)} selected questions to {selected_path}")
    click.echo(f"Preserved {preserved} previously completed question IDs; filled {len(selected) - preserved} new slots.")
    for task in config.questions.tasks:
        click.echo(f"  {task}: {counts[task]}")


@main.command("estimate")
@click.pass_context
def estimate(ctx):
    """Prints call counts and an approximate cost. Run before pilot/run."""
    config: HarnessConfig = ctx.obj["config"]
    n_per_model_pilot = config.questions.pilot_count * len(config.conditions) * config.n_runs
    n_per_model_full = config.questions.total_count * len(config.conditions) * config.n_runs

    click.echo(f"pilot: {n_per_model_pilot} calls per model")
    click.echo(_estimate_cost(config, n_per_model_pilot))
    click.echo(f"\nrun (full set): {n_per_model_full} calls per model")
    click.echo(_estimate_cost(config, n_per_model_full))


@main.command("dry-run")
@click.option("--full", is_flag=True, help="Use the full question set instead of the pilot subset.")
@click.pass_context
def dry_run(ctx, full):
    """Runs the full pipeline against the mock provider only. Never costs money."""
    config: HarnessConfig = ctx.obj["config"]
    data_dir = ctx.obj["data_dir"]
    selected = _get_or_select_questions(config, data_dir, ctx.obj["selected_path"])
    subset = selected if full else selected[: config.questions.pilot_count]
    questions_by_id = _questions_by_id(config, data_dir)

    results_path = ctx.obj["results_dir"] / "dryrun_mock.jsonl"
    for model_name in ("anthropic", "openai"):
        plan = build_plan(subset, questions_by_id, config, model_name)
        provider = MockProvider(model_id=f"mock-{model_name}")
        summary = run_plan(plan, provider, results_path)
        click.echo(f"{model_name}: {summary}")
    click.echo(f"Wrote mock results to {results_path}")


def _confirm_and_run(ctx, model_names: list[str], subset, build_provider, *, skip_confirm: bool = False):
    config: HarnessConfig = ctx.obj["config"]
    data_dir = ctx.obj["data_dir"]
    questions_by_id = _questions_by_id(config, data_dir)

    total_new_calls = 0
    plans = {}
    for model_name in model_names:
        plan = build_plan(subset, questions_by_id, config, model_name)
        plans[model_name] = plan
        results_path = ctx.obj["results_dir"] / f"{model_name}.jsonl"
        existing = load_existing_keys(results_path)
        new_calls = sum(1 for pc in plan if pc.key not in existing)
        total_new_calls += new_calls
        click.echo(f"{model_name}: {new_calls} new calls needed ({len(plan) - new_calls} already done)")

    click.echo(_estimate_cost(config, max(len(p) for p in plans.values())))
    if total_new_calls == 0:
        click.echo("Nothing new to run.")
        return

    if not skip_confirm and not click.confirm(
        f"\nThis will make {total_new_calls} REAL, PAID API call(s). Continue?", default=False
    ):
        click.echo("Aborted. No calls made.")
        return

    for model_name, plan in plans.items():
        provider = build_provider(model_name)
        results_path = ctx.obj["results_dir"] / f"{model_name}.jsonl"
        summary = run_plan(plan, provider, results_path)
        click.echo(f"{model_name}: {summary}")


def _build_real_provider(config: HarnessConfig, model_name: str):
    if model_name == "anthropic":
        from .providers.anthropic_provider import AnthropicProvider

        return AnthropicProvider(config.models.anthropic)
    if model_name == "openai":
        from .providers.openai_provider import OpenAIProvider

        return OpenAIProvider(config.models.openai)
    raise ValueError(model_name)


@main.command("pilot")
@click.option("--yes", is_flag=True, help="Skip the interactive confirmation prompt.")
@click.pass_context
def pilot(ctx, yes):
    """Runs the 5-question pilot against the real providers. Costs money."""
    config: HarnessConfig = ctx.obj["config"]
    selected = _get_or_select_questions(config, ctx.obj["data_dir"], ctx.obj["selected_path"])
    subset = selected[: config.questions.pilot_count]
    _confirm_and_run(
        ctx,
        ["anthropic", "openai"],
        subset,
        lambda name: _build_real_provider(config, name),
        skip_confirm=yes,
    )


@main.command("run")
@click.option("--yes", is_flag=True, help="Skip the interactive confirmation prompt.")
@click.pass_context
def run(ctx, yes):
    """Runs the full selected set against the real providers. Costs money."""
    config: HarnessConfig = ctx.obj["config"]
    selected = _get_or_select_questions(config, ctx.obj["data_dir"], ctx.obj["selected_path"])
    _confirm_and_run(
        ctx,
        ["anthropic", "openai"],
        selected,
        lambda name: _build_real_provider(config, name),
        skip_confirm=yes,
    )


def _batch_lock(callback):
    @wraps(callback)
    def locked(ctx, *args, **kwargs):
        import fcntl
        directory = ctx.obj["results_dir"].parent / "batches"
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / ".operation.lock").open("a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise click.ClickException("Another batch operation is running; wait for it to finish.") from exc
            return callback(ctx, *args, **kwargs)
    return locked


def _batch_cost(config, model_name, n_calls):
    import math
    cfg = getattr(config.models, model_name)
    if not n_calls:
        return 0.0
    prices = (cfg.price_per_million_input_tokens, cfg.price_per_million_output_tokens)
    if any(p is None or not math.isfinite(p) or p < 0 for p in prices):
        raise click.ClickException(f"{model_name}: valid input/output prices are required before estimating or submitting.")
    estimate = config.estimate
    return n_calls * (estimate.assumed_input_tokens_per_call * prices[0] + estimate.assumed_output_tokens_per_call * prices[1]) / 1_000_000 * estimate.batch_discount


def _build_new_batch_plans(ctx, config, selected, questions_by_id, model_names, completed_manifest, limit_new_questions=None):
    batch_dir = ctx.obj["results_dir"].parent / "batches"
    completed_question_ids = question_ids_from_manifest(completed_manifest)
    historical_fingerprints = question_fingerprints_from_manifest(completed_manifest)
    historical = json.loads(completed_manifest.read_text()) if completed_manifest.exists() else {}
    from .prompts import VISIBLE_EXPLANATION_INSTRUCTION, SUGGESTED_ANSWER_TEMPLATE
    from .providers.openai_provider import build_request as openai_request
    from .providers.anthropic_provider import build_request as anthropic_request
    new_plans: dict[str, list] = {}
    for name in model_names:
        plan = build_plan(selected, questions_by_id, config, name)
        existing = load_existing_keys(ctx.obj["results_dir"] / f"{name}.jsonl")
        builder = openai_request if name == "openai" else anthropic_request
        request = builder(getattr(config.models, name), "")
        settings = {k: v for k, v in request.items() if k not in ("input", "messages")}
        historical_compatible = (settings == historical.get("request_settings", {}).get(name)
                                 and VISIBLE_EXPLANATION_INSTRUCTION == historical.get("output_instruction")
                                 and SUGGESTED_ANSWER_TEMPLATE == historical.get("cue_template"))
        pending = pending_batch_keys(batch_dir, name)
        new_plan = [
            pc for pc in plan
            if pc.key not in existing
            and pc.key not in pending
            and not (historical_compatible and pc.question.source_question_id in completed_question_ids
                     and pc.question.fingerprint == historical_fingerprints.get(pc.question.source_question_id)
                     and pc.condition in historical.get("conditions", []) and pc.run_index in historical.get("run_indices", []))
        ]
        if limit_new_questions is not None:
            allowed_ids = []
            seen_ids = set()
            for pc in new_plan:
                qid = pc.question.question_id
                if qid not in seen_ids:
                    seen_ids.add(qid)
                    allowed_ids.append(qid)
                if len(allowed_ids) >= limit_new_questions:
                    break
            allowed = set(allowed_ids)
            new_plan = [pc for pc in new_plan if pc.question.question_id in allowed]
        new_plans[name] = new_plan
    return new_plans


@main.command("batch-estimate")
@click.option("--model", "model_name", type=click.Choice(["both", "anthropic", "openai"]), default="both", show_default=True)
@click.option("--completed-manifest", type=click.Path(path_type=Path), default=ROOT / "data" / "completed_question_ids.json", help="Question IDs from earlier completed experiments to exclude.")
@click.option("--limit-new-questions", type=click.IntRange(min=1), default=None, help="Estimate only the first N new question groups.")
@click.option("--openai-budget", type=click.FloatRange(min=0), default=None)
@click.option("--anthropic-budget", type=click.FloatRange(min=0), default=None)
@click.pass_context
def batch_estimate(ctx, model_name, completed_manifest, limit_new_questions, openai_budget, anthropic_budget):
    """Estimate a Batch submission without contacting either provider."""
    config: HarnessConfig = ctx.obj["config"]
    selected = _get_or_select_questions(config, ctx.obj["data_dir"], ctx.obj["selected_path"])
    questions_by_id = _questions_by_id(config, ctx.obj["data_dir"])
    model_names = ["anthropic", "openai"] if model_name == "both" else [model_name]
    new_plans = _build_new_batch_plans(
        ctx, config, selected, questions_by_id, model_names, completed_manifest, limit_new_questions
    )
    for name in model_names:
        cost = _batch_cost(config, name, len(new_plans[name]))
        budget = anthropic_budget if name == "anthropic" else openai_budget
        budget_text = f" vs estimated-spend limit ${budget:.2f}" if budget is not None else ""
        click.echo(f"{name}: {len(new_plans[name])} new calls, estimated Batch cost ${cost:.2f}{budget_text}")
    click.echo("Token assumptions are not a maximum-spend guarantee; calibrate with a small batch.")
    click.echo("No provider batch was submitted.")


@main.command("batch-submit")
@click.option("--model", "model_name", type=click.Choice(["both", "anthropic", "openai"]), default="both", show_default=True)
@click.option("--openai-budget", type=click.FloatRange(min=0), default=None, help="Maximum estimated OpenAI spend for this submission.")
@click.option("--anthropic-budget", type=click.FloatRange(min=0), default=None, help="Maximum estimated Anthropic spend for this submission.")
@click.option("--completed-manifest", type=click.Path(path_type=Path), default=ROOT / "data" / "completed_question_ids.json", help="Question IDs from earlier completed experiments to exclude from new paid batches.")
@click.option("--limit-new-questions", type=click.IntRange(min=1), default=None, help="Submit at most this many new question groups in this batch. Useful for a small smoke batch.")
@click.option("--yes", is_flag=True, help="Skip the interactive confirmation prompt.")
@click.pass_context
@_batch_lock
def batch_submit(ctx, model_name, openai_budget, anthropic_budget, completed_manifest, limit_new_questions, yes):
    """Submit missing calls, excluding completed and reserved request keys."""
    config: HarnessConfig = ctx.obj["config"]
    data_dir = ctx.obj["data_dir"]
    selected = _get_or_select_questions(config, data_dir, ctx.obj["selected_path"])
    questions_by_id = _questions_by_id(config, data_dir)
    model_names = ["anthropic", "openai"] if model_name == "both" else [model_name]
    new_plans = _build_new_batch_plans(
        ctx, config, selected, questions_by_id, model_names, completed_manifest, limit_new_questions
    )
    batch_dir = ctx.obj["results_dir"].parent / "batches"
    total_new_calls = 0
    for name in model_names:
        new_plan = new_plans[name]
        total_new_calls += len(new_plan)
        click.echo(f"{name}: {len(new_plan)} new calls (completed, submitted, or reserved earlier calls are excluded)")

        budget = anthropic_budget if name == "anthropic" else openai_budget
        est = _batch_cost(config, name, len(new_plan))
        click.echo(f"  estimated Batch cost: ${est:.2f}")
        if budget is not None and est > budget:
            raise click.ClickException(f"{name} estimate ${est:.2f} exceeds estimated-spend limit ${budget:.2f}. No batches submitted.")

    if total_new_calls == 0:
        click.echo("Nothing new to submit.")
        return
    click.echo("\nBatch API estimate (per provider):")
    click.echo("Based on configured token assumptions, not a maximum-spend guarantee.")
    if not yes and not click.confirm(
        f"\nSubmit {total_new_calls} real requests as asynchronous batches?", default=False
    ):
        click.echo("Aborted. No batches submitted.")
        return

    for name in model_names:
        plan = new_plans[name]
        if not plan:
            continue
        results_path = ctx.obj["results_dir"] / f"{name}.jsonl"
        if name == "anthropic":
            manifest = submit_anthropic_batch(
                plan, config.models.anthropic, batch_dir=batch_dir, results_path=results_path,
                protocol_version=config.protocol_version,
            )
            click.echo(f"anthropic batch submitted: {manifest['batch_id']} ({len(plan)} requests)")
        else:
            manifest = submit_openai_batch(
                plan, config.models.openai, batch_dir=batch_dir, results_path=results_path,
                protocol_version=config.protocol_version,
            )
            click.echo(f"openai batch submitted: {manifest['batch_id']} ({len(plan)} requests)")


@main.command("batch-status")
@click.option("--model", "model_name", type=click.Choice(["both", "anthropic", "openai"]), default="both", show_default=True)
@click.pass_context
@_batch_lock
def batch_status(ctx, model_name):
    """Refresh and print local batch manifest statuses."""
    batch_dir = ctx.obj["results_dir"].parent / "batches"
    providers = ["anthropic", "openai"] if model_name == "both" else [model_name]
    manifests = []
    for provider in providers:
        manifests.extend(sorted(batch_dir.glob(f"{provider}-*.json")))
    if not manifests:
        click.echo(f"No batch manifests found in {batch_dir}")
        return
    for path in manifests:
        manifest = load_manifest(path)
        if not manifest.get("batch_id"):
            click.echo(f"{path.name}: submission outcome unknown; reconcile with the provider before retrying.")
            continue
        try:
            status = (
                anthropic_batch_status(manifest["batch_id"]) if manifest["provider"] == "anthropic"
                else openai_batch_status(manifest["batch_id"])
            )
            manifest["status"] = status.get("processing_status", status.get("status", "unknown"))
            if status.get("request_counts") is not None:
                manifest["request_counts"] = status["request_counts"]
            manifest["last_checked_at"] = datetime.now().astimezone().isoformat()
            path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            click.echo(f"{manifest['provider']} {manifest['batch_id']}: status lookup failed: {exc}")
            continue
        counts = manifest.get("request_counts", {})
        progress = ""
        if counts:
            progress = f" completed={counts.get('completed', counts.get('succeeded', '?'))} failed={counts.get('failed', counts.get('errored', '?'))} total={counts.get('total', '?')}"
        click.echo(f"{manifest['provider']} {manifest['batch_id']}: {manifest['status']}{progress}")


@main.command("batch-collect")
@click.option("--model", "model_name", type=click.Choice(["both", "anthropic", "openai"]), default="both", show_default=True)
@click.option("--batch-id", default=None, help="Collect one specific provider batch; otherwise collect every completed local batch.")
@click.pass_context
@_batch_lock
def batch_collect(ctx, model_name, batch_id):
    """Collect completed batch results into the normal raw JSONL files."""
    batch_dir = ctx.obj["results_dir"].parent / "batches"
    providers = ["anthropic", "openai"] if model_name == "both" else [model_name]
    manifests = []
    for provider in providers:
        manifests.extend(sorted(batch_dir.glob(f"{provider}-*.json")))
    if batch_id:
        manifests = [p for p in manifests if load_manifest(p).get("batch_id") == batch_id]
    if not manifests:
        click.echo("No matching local batch manifests found.")
        return
    for path in manifests:
        manifest = load_manifest(path)
        if not manifest.get("batch_id"):
            click.echo(f"{path.name}: submission outcome unknown; reconcile with the provider before retrying.")
            continue
        if manifest.get("collected_at"):
            click.echo(f"{manifest['provider']} {manifest['batch_id']}: already collected")
            continue
        if manifest["provider"] == "anthropic":
            summary = collect_anthropic_batch(manifest)
        else:
            summary = collect_openai_batch(manifest)
        click.echo(f"{manifest['provider']} {manifest['batch_id']}: {summary}")


@main.command("analyze")
@click.option("--historical-dir", type=click.Path(path_type=Path, exists=True, file_okay=False), default=None, help="Combine a separate historical response directory with this run.")
@click.option("--summary-dir", type=click.Path(path_type=Path), default=None, help="Separate destination for this experiment’s analysis outputs.")
@click.pass_context
def analyze(ctx, historical_dir, summary_dir):
    """Computes metrics, the coding sheet and figures from existing raw results."""
    from .analysis.coding_sheet import build_coding_sheet
    from .analysis.figures import plot_accuracy, plot_flip_rates
    from .analysis.io_utils import write_dict_csv
    from .analysis.metrics import compute_metrics, split_needs_review, write_metrics_csv, write_needs_review_csv
    from .jsonl import read_jsonl

    config: HarnessConfig = ctx.obj["config"]
    results_dir = ctx.obj["results_dir"]
    summary_dir = summary_dir or DEFAULT_SUMMARY_DIR

    records_by_key = {}
    identities = {}
    directories = [results_dir] + ([historical_dir] if historical_dir else [])
    for directory in directories:
        for path in sorted(directory.glob("*.jsonl")):
            if path.name == "dryrun_mock.jsonl":
                continue
            for record in read_jsonl(path):
                key = record.get("key")
                if key is None:
                    # Legacy fixtures without a key still get duplicate identity checks.
                    key = (record["model_name"], record["question_id"], record["condition"], record["run_index"])
                if key in records_by_key:
                    if records_by_key[key] != record:
                        raise click.ClickException(f"Conflicting saved response key in {path}")
                    continue
                identity = (record["model_name"], record["question_id"], record["condition"], record["run_index"])
                if identity in identities:
                    raise click.ClickException(f"Duplicate response identity in {path}: {identity}")
                identities[identity] = key
                records_by_key[key] = record
    records = list(records_by_key.values())

    if not records:
        click.echo(f"No results found in {results_dir}")
        return

    _, needs_review = split_needs_review(records)
    write_needs_review_csv(needs_review, summary_dir / "needs_review.csv")

    metrics = compute_metrics(records)
    write_metrics_csv(metrics, summary_dir / "metrics_summary.csv")
    plot_flip_rates(metrics, summary_dir / "flip_rates.png")
    plot_accuracy(metrics, summary_dir / "accuracy.png")

    sheet_rows, key_rows = build_coding_sheet(records, config.seed)
    write_dict_csv(
        sheet_rows,
        summary_dir / "coding_sheet.csv",
        ["case_id", "visible_explanation", "rater_1_label", "rater_2_label", "llm_pre_label_DO_NOT_USE_IN_METRICS"],
    )
    write_dict_csv(
        key_rows,
        summary_dir / "coding_sheet_KEY_do_not_share_with_raters.csv",
        ["case_id", "model_name", "question_id", "run_index", "original_answer", "cue_answer", "cued_letter"],
    )

    click.echo(f"Wrote summary outputs to {summary_dir}")
    click.echo(f"{len(needs_review)} responses need manual review (needs_review.csv)")
    click.echo(f"{len(sheet_rows)} cue-flipped cases on the coding sheet")


@main.command("kappa")
@click.option("--coding-sheet", type=click.Path(path_type=Path), default=DEFAULT_SUMMARY_DIR / "coding_sheet.csv")
def kappa_cmd(coding_sheet):
    """Computes Cohen's kappa once both raters have filled in the coding sheet."""
    from .analysis.kappa import kappa_from_coding_sheet

    value = kappa_from_coding_sheet(coding_sheet)
    click.echo(f"Cohen's kappa: {value:.3f}")


if __name__ == "__main__":
    main()
