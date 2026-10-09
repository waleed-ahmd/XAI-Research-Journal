"""CLI entry point: `cot-harness <command>`.

Hard rule: no paid API call happens without the estimate being shown and
the caller explicitly confirming (--yes, or an interactive y/N prompt).
`dry-run` is always free: it only ever talks to the mock provider.
"""

from __future__ import annotations

from pathlib import Path

import click

from .config import DEFAULT_CONFIG_PATH, HarnessConfig, load_config
from .data.loader import load_all_questions
from .data.selection import (
    load_selected_questions,
    select_questions,
    write_selected_questions,
)
from .providers.mock import MockProvider
from .runner import build_plan, load_existing_keys, run_plan

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = ROOT / "data" / "bbh"
DEFAULT_SELECTED_PATH = ROOT / "data" / "selected_questions.json"
DEFAULT_RESULTS_DIR = ROOT / "results" / "raw"
DEFAULT_SUMMARY_DIR = ROOT / "results" / "summary"


def _questions_by_id(config: HarnessConfig, data_dir: Path) -> dict:
    questions = load_all_questions(config.questions.tasks, data_dir)
    return {q.question_id: q for q in questions}


def _get_or_select_questions(config: HarnessConfig, data_dir: Path, selected_path: Path):
    if selected_path.exists():
        return load_selected_questions(selected_path)
    selected = select_questions(config, data_dir)
    write_selected_questions(selected, selected_path)
    click.echo(f"Wrote {len(selected)} selected questions to {selected_path}")
    return selected


def _estimate_cost(config: HarnessConfig, n_calls_per_model: int) -> str:
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


@main.command("analyze")
@click.pass_context
def analyze(ctx):
    """Computes metrics, the coding sheet and figures from existing raw results."""
    import json

    from .analysis.coding_sheet import build_coding_sheet, write_csv
    from .analysis.figures import plot_accuracy, plot_flip_rates
    from .analysis.metrics import compute_metrics, split_needs_review, write_metrics_csv, write_needs_review_csv

    config: HarnessConfig = ctx.obj["config"]
    results_dir = ctx.obj["results_dir"]
    summary_dir = DEFAULT_SUMMARY_DIR

    records: list[dict] = []
    for path in sorted(results_dir.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as f:
            records.extend(json.loads(line) for line in f if line.strip())

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
    write_csv(
        sheet_rows,
        summary_dir / "coding_sheet.csv",
        ["case_id", "visible_explanation", "rater_1_label", "rater_2_label", "llm_pre_label_DO_NOT_USE_IN_METRICS"],
    )
    write_csv(
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
