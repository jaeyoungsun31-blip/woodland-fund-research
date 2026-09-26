"""Render the figures used by `writeup/research-report.md`.

One figure so far: the turnover budget, plotted log-log.

The five (turnover, crossover) pairs are transcribed from the journal, which
is the record of authority — `2026-09-03-planning-note-turnover-budget.md`
consolidates them and each is published in the results entry cited beside it.
They are not recomputed here, because recomputing them is
`scripts/reproduce_all.py`'s job and doing it in two places invites the two
places to disagree. This script draws what the journal says; that script
checks that what the journal says is true.

    .venv/bin/python scripts/make_writeup_figures.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

FIGURES = Path(__file__).resolve().parent.parent / "writeup" / "figures"

# label, annual turnover (turns), solved cost crossover (bps), source entry
OBSERVATIONS = [
    ("annual", 1.0896, 208.110, "v15"),
    ("semi-annual", 1.7057, 135.550, "v15"),
    ("quarterly", 2.5542, 85.991, "v15"),
    ("monthly", 4.5842, 52.516, "v15"),
    ("daily recon.", 21.736, 11.168, "v13"),
]

RETAIL_COST_LOW, RETAIL_COST_HIGH = 25.0, 50.0


def turnover_budget() -> Path:
    turnover = np.array([o[1] for o in OBSERVATIONS])
    crossover = np.array([o[2] for o in OBSERVATIONS])
    products = turnover * crossover
    k = float(products.mean())

    fig, ax = plt.subplots(figsize=(7.2, 5.0))
    grid = np.logspace(np.log10(0.8), np.log10(30.0), 200)

    ax.fill_between(grid, products.min() / grid, products.max() / grid,
                    color="#4c72b0", alpha=0.13, lw=0,
                    label=f"observed spread  K = {products.min():.0f}–{products.max():.0f}")
    ax.plot(grid, k / grid, color="#4c72b0", lw=1.6,
            label=f"c* = K / turnover,  K = {k:.0f} bps-turns")

    # The budget is where the fitted line passes through the cost band the
    # project actually faces: turnover from K/high to K/low.
    budget_low, budget_high = k / RETAIL_COST_HIGH, k / RETAIL_COST_LOW
    ax.axvspan(budget_low, budget_high, color="#55a868", alpha=0.13, lw=0,
               label=f"turnover budget  {budget_low:.1f}x–{budget_high:.1f}x")
    ax.axhspan(RETAIL_COST_LOW, RETAIL_COST_HIGH, color="#c44e52", alpha=0.10, lw=0)
    ax.axhline(RETAIL_COST_LOW, color="#c44e52", lw=0.9, ls="--")
    ax.axhline(RETAIL_COST_HIGH, color="#c44e52", lw=0.9, ls="--")
    ax.text(0.86, (RETAIL_COST_LOW * RETAIL_COST_HIGH) ** 0.5,
            "retail cost\n25–50 bps", color="#c44e52", fontsize=8,
            va="center", ha="left")
    ax.text((budget_low * budget_high) ** 0.5, 8.4,
            f"turnover budget\n{budget_low:.1f}x–{budget_high:.1f}x / yr",
            color="#3d7a52", fontsize=8, va="bottom", ha="center")

    for label, x, y, source in OBSERVATIONS:
        marker = "o" if source == "v15" else "s"
        ax.scatter([x], [y], s=44, marker=marker, zorder=5,
                   color="#2f2f2f" if source == "v15" else "#dd8452",
                   edgecolor="white", linewidth=0.8)
        offset = (9, 7) if source == "v15" else (-10, 12)
        align = "left" if source == "v15" else "right"
        ax.annotate(f"{label}\n{x:.2f}x, {y:.0f} bps", (x, y),
                    textcoords="offset points", xytext=offset,
                    fontsize=7.5, color="#2f2f2f", ha=align)

    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.8, 30.0)
    ax.set_ylim(7.0, 400.0)
    ax.set_xlabel("model-implied annual turnover (turns per year)")
    ax.set_ylabel("cost crossover c* (bps one-way)")
    ax.set_title("The turnover budget: crossover cost falls as 1 / turnover",
                 fontsize=11)
    ax.grid(True, which="both", lw=0.4, alpha=0.35)
    ax.legend(loc="upper right", fontsize=8, frameon=False)
    fig.text(0.5, 0.008,
             "Circles: v15 stale-cohort holding frequencies.  Square: v13 "
             "daily-reconstituted top three.  Both turnover figures are "
             "model-implied, not observed.",
             ha="center", fontsize=7, color="#555555")
    fig.tight_layout(rect=(0, 0.035, 1, 1))

    FIGURES.mkdir(parents=True, exist_ok=True)
    out = FIGURES / "turnover-budget.png"
    fig.savefig(out, dpi=200)
    plt.close(fig)
    print(f"K = {k:.1f} bps-turns  (spread {products.min():.1f}–{products.max():.1f}, "
          f"{100.0 * (products.max() - products.min()) / k:.1f}% of the mean)")
    print(f"wrote {out}")
    return out


def main() -> int:
    turnover_budget()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
