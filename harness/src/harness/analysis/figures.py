"""Matplotlib figures sized for an IEEE two-column layout (~3.45in wide)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

IEEE_COLUMN_FIGSIZE = (3.45, 2.6)


def plot_flip_rates(metrics: dict[str, dict], out_path: Path) -> None:
    models = list(metrics.keys())
    cue_rates = [metrics[m]["cue_flip"]["rate"] for m in models]
    cue_err = [
        [
            metrics[m]["cue_flip"]["rate"] - metrics[m]["cue_flip"]["ci_low"]
            for m in models
        ],
        [
            metrics[m]["cue_flip"]["ci_high"] - metrics[m]["cue_flip"]["rate"]
            for m in models
        ],
    ]
    baseline_rates = [metrics[m]["baseline_flip"]["rate"] for m in models]
    baseline_err = [
        [
            metrics[m]["baseline_flip"]["rate"] - metrics[m]["baseline_flip"]["ci_low"]
            for m in models
        ],
        [
            metrics[m]["baseline_flip"]["ci_high"] - metrics[m]["baseline_flip"]["rate"]
            for m in models
        ],
    ]

    fig, ax = plt.subplots(figsize=IEEE_COLUMN_FIGSIZE)
    x = range(len(models))
    width = 0.35
    ax.bar(
        [i - width / 2 for i in x], cue_rates, width, yerr=cue_err, capsize=3, label="Cue flip"
    )
    ax.bar(
        [i + width / 2 for i in x],
        baseline_rates,
        width,
        yerr=baseline_err,
        capsize=3,
        label="Baseline flip",
    )
    ax.set_xticks(list(x))
    ax.set_xticklabels(models, fontsize=7)
    ax.set_ylabel("Flip rate", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def plot_accuracy(metrics: dict[str, dict], out_path: Path) -> None:
    models = list(metrics.keys())
    conditions = sorted({c for m in models for c in metrics[m]["accuracy"]})

    fig, ax = plt.subplots(figsize=IEEE_COLUMN_FIGSIZE)
    width = 0.8 / max(len(conditions), 1)
    for ci, condition in enumerate(conditions):
        rates = [metrics[m]["accuracy"].get(condition, {}).get("rate", 0.0) for m in models]
        offsets = [i - 0.4 + ci * width + width / 2 for i in range(len(models))]
        ax.bar(offsets, rates, width, label=condition)
    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(models, fontsize=7)
    ax.set_ylabel("Accuracy", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
