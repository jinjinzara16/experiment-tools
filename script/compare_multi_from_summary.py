#!/usr/bin/env python3
import os
import json
import argparse
import numpy as np
import matplotlib.pyplot as plt

METRICS_DEFAULT = [
    "paths_total",
    "bitmap_cvg",
    "execs_per_sec",
    "execs_done",
    "pending_total",
    "pending_favs",
    "unique_crashes",
    "unique_hangs",
]


def load_summary(dir_path):
    path = os.path.join(dir_path, "summary.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"summary.json not found in {dir_path}")
    with open(path) as f:
        return json.load(f)


def collect_metric(summaries, metric):
    vals = []
    for s in summaries:
        if metric not in s:
            vals.append(None)
        else:
            vals.append(float(s[metric]["avg"]))
    return vals


def pretty_ylim(values):
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    vmin = min(vals)
    vmax = max(vals)
    if vmax == vmin:
        if vmax == 0:
            return (0, 1)
        return (vmin * 0.9, vmax * 1.1)
    margin = (vmax - vmin) * 0.2
    lo = max(0, vmin - margin)
    hi = vmax + margin
    return (lo, hi)


def plot_metric_bar(metric, labels, values, outdir, title_prefix=""):
    os.makedirs(outdir, exist_ok=True)
    x = np.arange(len(labels))

    fig, ax = plt.subplots()
    bars = ax.bar(x, [v if v is not None else 0 for v in values])

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel(metric)
    if title_prefix:
        ax.set_title(f"{title_prefix} – {metric} (avg)")
    else:
        ax.set_title(f"{metric} (avg)")

    ylim = pretty_ylim(values)
    if ylim:
        ax.set_ylim(*ylim)

    baseline = values[0] if values and values[0] is not None else None
    for i, (b, v) in enumerate(zip(bars, values)):
        if v is None:
            continue
        txt = f"{v:.2f}"
        if i > 0 and baseline not in (None, 0.0):
            delta = (v - baseline) / baseline * 100.0
            txt += f"\n({delta:+.1f}%)"
        ax.text(
            b.get_x() + b.get_width() / 2,
            b.get_height(),
            txt,
            ha="center",
            va="bottom",
            fontsize=8,
        )

    fig.tight_layout()
    out_path = os.path.join(outdir, f"{metric}.png")
    fig.savefig(out_path)
    plt.close(fig)
    print(f"[INFO] saved {out_path}")


def print_markdown_table(metric, labels, values):
    baseline = values[0] if values and values[0] is not None else None

    header = ["metric"]
    row_vals = [metric]
    row_deltas = ["Δ vs " + labels[0] + " (%)"]

    for i, (lab, v) in enumerate(zip(labels, values)):
        header.append(f"{lab} (avg)")
        if v is None:
            row_vals.append("N/A")
        else:
            row_vals.append(f"{v:.2f}")

        if i == 0:
            continue
        if v is None or baseline in (None, 0.0):
            row_deltas.append("N/A")
        else:
            delta = (v - baseline) / baseline * 100.0
            row_deltas.append(f"{delta:+.1f}%")

    print("| " + " | ".join(header) + " |")
    print("| " + " | ".join(["---"] * len(header)) + " |")
    print("| " + " | ".join(row_vals) + " |")

    if len(row_deltas) > 1:
        delta_row = ["Δ vs " + labels[0] + " (%)"]
        delta_row.extend(row_deltas[1:])
        print("| " + " | ".join(delta_row) + " |")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dirs",
        nargs="+",
        required=True,
        help="experiment dirs (each contains summary.json)",
    )
    ap.add_argument(
        "--labels",
        nargs="+",
        required=True,
        help="labels for each dir (same length as --dirs)",
    )
    ap.add_argument(
        "--metrics",
        nargs="+",
        default=METRICS_DEFAULT,
        help="metrics to compare (default: common AFL metrics)",
    )
    ap.add_argument(
        "--outdir",
        required=True,
        help="directory to save plots",
    )
    ap.add_argument(
        "--title-prefix",
        default="",
        help="prefix for plot titles (e.g., readelf / objdump)",
    )
    args = ap.parse_args()

    if len(args.dirs) != len(args.labels):
        raise SystemExit("len(dirs) != len(labels)")

    summaries = [load_summary(d) for d in args.dirs]

    print(f"# Aggregate comparison ({args.title_prefix})\n")

    for metric in args.metrics:
        values = collect_metric(summaries, metric)
        print_markdown_table(metric, args.labels, values)
        plot_metric_bar(metric, args.labels, values, args.outdir, args.title_prefix)


if __name__ == "__main__":
    main()
