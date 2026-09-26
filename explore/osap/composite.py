"""OSAP composite-signal test, exactly as in composite_precommit.md.

All 212 predictors, none selected. Writes raw/derived/composite_*.{csv,json,md}.
"""

import json
import math

import numpy as np
import pandas as pd
from triage import OUT, load

MIN_BREADTH = 10
NW_LAG = 6
WINDOWS = {
    "full": (None, "2024-12-31"),
    "post2000": ("2000-01-01", "2024-12-31"),
    "2015_2024": ("2015-01-01", "2024-12-31"),
}
PRIMARY = ("vw", "post_pub", "2015_2024")


def composite(frame, pub_year=None):
    """Equal-weighted mean of available LS returns; post-pub mask if pub_year given."""
    data = frame
    if pub_year is not None:
        live = np.greater.outer(frame.index.year.to_numpy(), pub_year.to_numpy())
        data = frame.where(live)
    count = data.notna().sum(axis=1)
    return data.mean(axis=1).where(count >= MIN_BREADTH), count


def newey_west_se(x, lag=NW_LAG):
    x = np.asarray(x, dtype=float)
    n = len(x)
    e = x - x.mean()
    s = e @ e / n
    for k in range(1, lag + 1):
        s += 2 * (1 - k / (lag + 1)) * (e[k:] @ e[:-k]) / n
    return math.sqrt(s / n)


def worst_12m(x):
    growth = (1 + np.asarray(x, dtype=float) / 100).cumprod()
    growth = np.concatenate([[1.0], growth])
    return float((growth[12:] / growth[:-12]).min() - 1) if len(x) >= 12 else float("nan")


def stats(series, count):
    rows = {}
    for name, (lo, hi) in WINDOWS.items():
        mask = series.notna() & (series.index <= pd.Timestamp(hi))
        if lo:
            mask &= series.index >= pd.Timestamp(lo)
        x, c = series[mask], count[mask]
        if len(x) < 12:
            rows[name] = {"months": int(len(x))}
            continue
        se_nw = newey_west_se(x)
        rows[name] = {
            "start": x.index.min().strftime("%Y-%m"),
            "end": x.index.max().strftime("%Y-%m"),
            "months": int(len(x)),
            "mean": float(x.mean()),
            "nw_t": float(x.mean() / se_nw),
            "sharpe_ann": float(x.mean() / x.std(ddof=1) * math.sqrt(12)),
            "worst_12m": worst_12m(x),
            "sd": float(x.std(ddof=1)),
            "se_nw": se_nw,
            "se_iid": float(x.std(ddof=1) / math.sqrt(len(x))),
            "breadth_min": int(c.min()),
            "breadth_median": float(c.median()),
        }
    return rows


def composites(doc, returns, subset=None):
    names = doc.index if subset is None else subset
    out, series = {}, {}
    for label in ("vw", "op"):
        frame = returns[label][names]
        for kind, pub in (("all", None), ("post_pub", doc.loc[names, "Year"])):
            s, c = composite(frame, pub)
            out[(label, kind)] = stats(s, c)
            series[f"{label}_{kind}"] = s
            series[f"{label}_{kind}_n"] = c
    return out, pd.DataFrame(series)


def diversification(frame):
    window = frame.loc["2015-01-01":"2024-12-31"]
    complete = window.columns[window.notna().sum() == len(window)]
    excluded = sorted(set(window.columns) - set(complete), key=str.lower)
    corr = np.corrcoef(window[complete].to_numpy(), rowvar=False)
    off = corr[~np.eye(len(corr), dtype=bool)]
    eig = np.sort(np.linalg.eigvalsh(corr))[::-1]
    share = np.cumsum(eig) / eig.sum()
    return {
        "months": int(len(window)),
        "predictors": int(len(complete)),
        "excluded_incomplete": excluded,
        "mean_pairwise_corr": float(off.mean()),
        "median_pairwise_corr": float(np.median(off)),
        "mean_abs_pairwise_corr": float(np.abs(off).mean()),
        "n_eff_participation_ratio": float(eig.sum() ** 2 / (eig**2).sum()),
        "eigs_for_90pct": int(np.searchsorted(share, 0.90) + 1),
        "first_eig_share": float(eig[0] / eig.sum()),
    }


def table(results, window_keys=tuple(WINDOWS)):
    lines = [
        "| Composite | Window | Months | Breadth min/median | Mean %/mo | NW t (6) "
        "| Sharpe (ann.) | Worst 12m |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for (label, kind), rows in results.items():
        for w in window_keys:
            r = rows[w]
            if "mean" not in r:
                lines.append(
                    f"| {label.upper()} {kind} | {w} | {r['months']} | — | — | — | — | — |"
                )
                continue
            lines.append(
                f"| {label.upper()} {kind} | {w} ({r['start']}–{r['end']}) | {r['months']} "
                f"| {r['breadth_min']}/{r['breadth_median']:.0f} | {r['mean']:+.3f} "
                f"| {r['nw_t']:+.2f} | {r['sharpe_ann']:.2f} | {r['worst_12m']:+.1%} |"
            )
    return "\n".join(lines) + "\n"


def main():
    doc, returns = load()
    headline, series = composites(doc, returns)
    OUT.mkdir(parents=True, exist_ok=True)
    series.to_csv(OUT / "composite_series.csv")
    by_cat = {}
    cat_md = []
    for cat, sub in doc.groupby("Cat.Data"):
        res, _ = composites(doc, returns, sub.index)
        by_cat[cat] = {f"{a}_{b}": v for (a, b), v in res.items()}
        cat_md.append(f"#### {cat} ({len(sub)} predictors)\n\n" + table(res))
    div = diversification(returns["vw"])
    primary = headline[PRIMARY[:2]][PRIMARY[2]]
    power = {
        "window": PRIMARY[2],
        "sd": primary["sd"],
        "months": primary["months"],
        "mde_t2_nw": 2 * primary["se_nw"],
        "mde_t2_iid": 2 * primary["se_iid"],
    }
    summary = {
        "primary": {"composite": "vw post_pub", "window": PRIMARY[2], **primary},
        "headline": {f"{a}_{b}": v for (a, b), v in headline.items()},
        "diversification_vw_2015_2024": div,
        "power": power,
        "by_category": by_cat,
    }
    (OUT / "composite_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (OUT / "composite_headline.md").write_text(table(headline))
    (OUT / "composite_by_category.md").write_text("\n".join(cat_md))
    print(table(headline))
    print(json.dumps({"primary": summary["primary"], "div": div, "power": power}, indent=2))


if __name__ == "__main__":
    main()
