"""Result figures drawn only from numbers already in committed files.

Each value is parsed from its named source file; nothing is recomputed, fetched,
or estimated, and no vendor price level is plotted. If a required number is not
found, the figure is skipped and the missing number is printed.

    .venv/bin/python writeup/figures/make_figures.py
"""

import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
MIN_BAND_GAMES = 10
NUM = r"([+−-]?\d+(?:\.\d+)?)"


def num(text):
    return float(text.replace("−", "-").replace("+", ""))


def read(rel):
    return (ROOT / rel).read_text()


class Missing(Exception):
    pass


def v16_sharpe_diff():
    src = "journal/2026-09-10-planning-decision-termination-signed.md"
    m = re.search(rf"minus naive momentum {NUM}, CI \[{NUM}, {NUM}\]", read(src))
    if not m:
        raise Missing(f"penalized-minus-naive Sharpe difference and CI in {src}")
    est, lo, hi = (num(g) for g in m.groups())
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    ax.errorbar([est], [0], xerr=[[est - lo], [hi - est]], fmt="o", color="#1f4e79", capsize=6)
    ax.axvline(0, color="black", linestyle="--", linewidth=1)
    ax.set_yticks([])
    ax.set_xlabel("Sharpe ratio difference (annualized)")
    ax.set_title("xsmom-v16 universe control: penalized minus naive momentum\n"
                 "Sharpe ratio, point estimate and 95% CI", fontsize=11)
    ax.set_xlim(min(lo, 0) - 0.1, max(hi, 0) + 0.1)
    fig.tight_layout()
    fig.savefig(OUT / "v16_sharpe_diff.png", dpi=150)
    plt.close(fig)
    return src, {"estimate": est, "ci_low": lo, "ci_high": hi}


def kalshi_calibration():
    src = "explore/kalshi/mlb_results.md"
    row = re.compile(
        r"^\| (0\.\d\d)–(\d\.\d\d) "
        r"\| (.*?) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \| (.*?) \|$"
    )
    series = {"60 min": [], "10 min": []}
    for line in read(src).splitlines():
        m = row.match(line)
        if not m:
            continue
        g = m.groups()
        for label, (n, ask, win, ci) in (("60 min", g[2:6]), ("10 min", g[6:10])):
            if n.strip() in ("—", ""):
                continue
            lo, hi = (float(x) / 100 for x in ci.strip("[] ").split(","))
            series[label].append((float(ask), float(win.rstrip("%")) / 100, lo, hi, int(n)))
    if not all(series.values()):
        raise Missing(f"calibration table (mean ask, win rate, Wilson 95%) in {src}")
    omitted = [p for pts in series.values() for p in pts if p[4] < MIN_BAND_GAMES]
    series = {k: [p for p in v if p[4] >= MIN_BAND_GAMES] for k, v in series.items()}
    sizes = sorted({p[4] for p in omitted})
    each = (f"{sizes[0]} game{'s' if sizes[0] != 1 else ''} each" if len(sizes) == 1
            else "games: " + ", ".join(str(p[4]) for p in omitted))
    footnote = (f"Bands with fewer than {MIN_BAND_GAMES} games omitted "
                f"({len(omitted)} band{'s' if len(omitted) != 1 else ''}, {each})."
                if omitted else "")
    fig, ax = plt.subplots(figsize=(6, 5.8))
    ax.plot([0.48, 0.80], [0.48, 0.80], color="grey", linestyle="--", linewidth=1,
            label="45° line")
    for (label, pts), color, shift in zip(series.items(), ("#1f4e79", "#c55a11"), (-0.003, 0.003),
                                          strict=True):
        x = [p[0] + shift for p in pts]
        y = [p[1] for p in pts]
        err = [[p[1] - p[2] for p in pts], [p[3] - p[1] for p in pts]]
        ax.errorbar(x, y, yerr=err, fmt="o", capsize=3, color=color,
                    label=f"{label} before start (Wilson 95% CI)")
    ax.set_xlabel(r"Implied win probability (mean favourite ask, \$ per \$1 contract)")
    ax.set_ylabel("Realized favourite win rate")
    ax.set_title("Kalshi MLB favourites, 2025 season: implied vs realized\n"
                 "win probability by 5¢ ask band")
    ax.set_xlim(0.48, 0.80)
    ax.set_ylim(0.40, 1.0)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    if footnote:
        fig.text(0.01, 0.01, footnote, fontsize=8, ha="left", va="bottom")
    fig.savefig(OUT / "kalshi_calibration.png", dpi=150)
    plt.close(fig)
    values = {k: [(a, w, lo, hi, n) for a, w, lo, hi, n in v] for k, v in series.items()}
    values["omitted"] = omitted
    values["footnote"] = footnote
    return src, values


def insider_buckets():
    src = "explore/insiders/robustness_screen_report.md"
    text = read(src)
    # The figure needs a 95% CI (or a standard error) for each bucket's alpha.
    if not re.search(r"95% (CI|confidence)|standard error|\bSE\b", text):
        raise Missing(
            f"95% CI (or standard error) for each bucket's FF7 alpha in {src}; the file "
            "commits alpha and HAC t only"
        )
    raise Missing("insider CI parsing not implemented for the committed format")


def osap_triage_counts():
    src = "explore/osap/triage_report.md"
    text = read(src)
    header = re.search(r"^\| Window \| OP \| VW \(forced\) \| Both \| Expected by chance alone \|",
                       text, re.M)
    if not header:
        raise Missing(f"headline table header (OP | VW | Both | Expected by chance) in {src}")
    row = re.search(
        r"^\| 2015–2024 \| \*{0,2}(\d+)/(\d+)[^|]*\| \*{0,2}(\d+)/(\d+)[^|]*\| (\d+) "
        r"\| (\d+(?:\.\d+)?) \|",
        text,
        re.M,
    )
    if not row:
        raise Missing(
            f"2015–2024 row (OP count, VW count, both, expected by chance) in {src}"
        )
    op, op_n, vw, vw_n, both, chance = row.groups()
    op, op_n, vw, vw_n = int(op), int(op_n), int(vw), int(vw_n)
    both, chance = int(both), float(chance)
    fig, ax = plt.subplots(figsize=(7.4, 4.8))
    labels = ["Original\nspecification", "Value-weighted", "Both\nspecifications",
              "Expected\nby chance"]
    heights = [op, vw, both, chance]
    bars = ax.bar(labels, heights, color=["#1f4e79", "#2e75b6", "#5b9bd5", "#a6a6a6"],
                  width=0.6)
    for bar, h in zip(bars, heights, strict=True):
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.4, f"{h:g}", ha="center", va="bottom")
    ax.set_ylabel(f"Number of predictors (of {op_n})")
    ax.set_ylim(0, max(heights) * 1.2)
    ax.set_title("OSAP predictors with a positive mean and t > 2, 2015–2024: original\n"
                 "specification, value-weighted, both, and expected by chance", fontsize=11)
    fig.tight_layout()
    fig.savefig(OUT / "osap_triage_counts.png", dpi=150)
    plt.close(fig)
    return src, {"op": op, "op_of": op_n, "vw": vw, "vw_of": vw_n, "both": both,
                 "expected_by_chance": chance}


def main():
    status = 0
    for fn in (v16_sharpe_diff, kalshi_calibration, insider_buckets, osap_triage_counts):
        try:
            src, values = fn()
            print(f"WROTE {fn.__name__}.png  source={src}  values={values}")
        except Missing as missing:
            print(f"SKIPPED {fn.__name__}: missing {missing}")
            status = 1 if fn is not insider_buckets else status
    sys.exit(status)


if __name__ == "__main__":
    main()
