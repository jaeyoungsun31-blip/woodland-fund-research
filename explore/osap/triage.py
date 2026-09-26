"""Anomaly triage on Open Source Asset Pricing long-short returns (meta-research).

Descriptive only: no predictor is selected, ranked or recommended. Reads the
gitignored raw/ files fetched by fetch.py and writes raw/derived/*.csv plus
raw/derived/summary.json, which triage_report.md is built from.

Windows (per predictor, from SignalDoc.csv; calendar months inclusive):
  in-sample        Jan SampleStartYear .. Dec SampleEndYear
  post-publication Jan (Year + 1)      .. Dec 2024
  recent           Jan 2015            .. Dec 2024
t is mean / (sd / sqrt(n)) on monthly long-short returns (percent per month).
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
OUT = RAW / "derived"
END = pd.Timestamp("2024-12-31")
WINDOWS = ("in", "post", "recent")
MIN_MONTHS = 12


def load():
    doc = pd.read_csv(RAW / "SignalDoc.csv")
    doc = doc[doc["Cat.Signal"] == "Predictor"].set_index("Acronym")
    op = pd.read_csv(RAW / "PredictorLSretWide.csv", parse_dates=["date"]).set_index("date")
    vw_long = pd.read_csv(
        RAW / "PredictorAltPorts_LiqScreen_VWforce.csv",
        usecols=["signalname", "port", "date", "ret"],
        dtype={"port": str},
        parse_dates=["date"],
    )
    vw = vw_long[vw_long["port"] == "LS"].pivot(index="date", columns="signalname", values="ret")
    missing = [s for s in doc.index if s not in op.columns or s not in vw.columns]
    if missing:
        raise SystemExit(f"predictors missing from a return file: {missing}")
    return doc, {"op": op[doc.index], "vw": vw[doc.index]}


def bounds(row):
    return {
        "in": (
            pd.Timestamp(int(row.SampleStartYear), 1, 1),
            pd.Timestamp(int(row.SampleEndYear), 12, 31),
        ),
        "post": (pd.Timestamp(int(row.Year) + 1, 1, 1), END),
        "recent": (pd.Timestamp(2015, 1, 1), END),
    }


def window_stats(series, lo, hi):
    x = series[(series.index >= lo) & (series.index <= hi)].dropna()
    n = len(x)
    if n < MIN_MONTHS:
        return {"n": n, "mean": np.nan, "t": np.nan}
    mean = float(x.mean())
    return {"n": n, "mean": mean, "t": mean / (float(x.std(ddof=1)) / np.sqrt(n))}


def per_predictor(doc, returns):
    rows = []
    for name, row in doc.iterrows():
        b = bounds(row)
        for label, frame in returns.items():
            rec = {"predictor": name, "dataset": label}
            for w in WINDOWS:
                s = window_stats(frame[name], *b[w])
                rec.update({f"{w}_{k}": v for k, v in s.items()})
            rec["post_in_ratio"] = (
                rec["post_mean"] / rec["in_mean"] if rec["in_mean"] > 0 else np.nan
            )
            rows.append(rec)
    table = pd.DataFrame(rows)
    meta = doc[
        [
            "Cat.Data",
            "Cat.Economic",
            "Portfolio Period",
            "Stock Weight",
            "Year",
            "SampleStartYear",
            "SampleEndYear",
        ]
    ]
    return table.merge(meta, left_on="predictor", right_index=True).sort_values(
        ["dataset", "predictor"]
    )


def t_sf(t, df):
    """P(T_df > t) by integrating the Student-t density (no SciPy in this venv)."""
    grid = np.linspace(t, t + 400.0, 400_001)
    log_c = math.lgamma((df + 1) / 2) - math.lgamma(df / 2) - 0.5 * math.log(df * math.pi)
    density = np.exp(log_c - (df + 1) / 2 * np.log1p(grid**2 / df))
    return float(np.sum((density[1:] + density[:-1]) / 2) * (grid[1] - grid[0]))


def expected_by_chance(table, window):
    """E[# with t > 2 and mean > 0] if every true mean were zero (per-series df)."""
    n = table[f"{window}_n"]
    n = n[n >= MIN_MONTHS]
    return float(sum(t_sf(2.0, int(k) - 1) for k in n))


def pass_share(sub, window):
    ok = sub[f"{window}_t"].notna()
    hit = (sub[f"{window}_mean"] > 0) & (sub[f"{window}_t"] > 2)
    return int(hit.sum()), int(ok.sum())


def ratio_summary(r):
    r = r.dropna()
    q = r.quantile([0.1, 0.25, 0.5, 0.75, 0.9])
    return {
        "n": int(len(r)),
        "mean": float(r.mean()),
        "p10": float(q[0.1]),
        "p25": float(q[0.25]),
        "median": float(q[0.5]),
        "p75": float(q[0.75]),
        "p90": float(q[0.9]),
        "share_below_0": float((r < 0).mean()),
        "share_0_to_0.5": float(((r >= 0) & (r < 0.5)).mean()),
        "share_0.5_to_1": float(((r >= 0.5) & (r < 1)).mean()),
        "share_at_least_1": float((r >= 1).mean()),
    }


def grouped(table, column):
    out = []
    for (label, value), sub in table.groupby(["dataset", table[column].fillna("NA")]):
        rec = {"dataset": label, column: value, "predictors": len(sub)}
        for w in ("post", "recent"):
            hit, n = pass_share(sub, w)
            rec[f"{w}_pos_t2"] = hit
            rec[f"{w}_n"] = n
        rec["median_in_mean"] = float(sub["in_mean"].median())
        rec["median_post_mean"] = float(sub["post_mean"].median())
        rec["median_recent_mean"] = float(sub["recent_mean"].median())
        rec["median_post_in_ratio"] = float(sub["post_in_ratio"].median())
        out.append(rec)
    return pd.DataFrame(out)


def appendix(table):
    """Alphabetical per-predictor table (not a ranking) for the report appendix."""

    def cell(row, w):
        return "—" if pd.isna(row[f"{w}_t"]) else f"{row[f'{w}_mean']:+.2f} ({row[f'{w}_t']:+.1f})"

    wide = table.set_index(["predictor", "dataset"])
    lines = [
        "| Predictor | Pub. | OP in | OP post | OP 2015–24 | VW in | VW post | VW 2015–24 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name in sorted(table["predictor"].unique(), key=str.lower):
        op, vw = wide.loc[(name, "op")], wide.loc[(name, "vw")]
        cells = [cell(op, w) for w in WINDOWS] + [cell(vw, w) for w in WINDOWS]
        lines.append(f"| {name} | {int(op['Year'])} | " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def group_markdown(g, column, label):
    head = (
        f"| {label} | N | OP post: +t>2 | VW post: +t>2 | OP 2015–24: +t>2 "
        "| VW 2015–24: +t>2 | OP median mean in / post / 15–24 "
        "| VW median mean in / post / 15–24 | Median post/in ratio OP / VW |"
    )
    lines = [head, "|---|---:|---:|---:|---:|---:|---|---|---|"]
    for key in dict.fromkeys(g[column]):
        o = g[(g["dataset"] == "op") & (g[column] == key)].iloc[0]
        v = g[(g["dataset"] == "vw") & (g[column] == key)].iloc[0]

        def means(r):
            return (
                f"{r.median_in_mean:+.2f} / {r.median_post_mean:+.2f} / {r.median_recent_mean:+.2f}"
            )

        lines.append(
            f"| {key} | {o.predictors} | {o.post_pos_t2}/{o.post_n} | {v.post_pos_t2}/{v.post_n} "
            f"| {o.recent_pos_t2}/{o.recent_n} | {v.recent_pos_t2}/{v.recent_n} "
            f"| {means(o)} | {means(v)} "
            f"| {o.median_post_in_ratio:.2f} / {v.median_post_in_ratio:.2f} |"
        )
    return "\n".join(lines) + "\n"


def main():
    doc, returns = load()
    table = per_predictor(doc, returns)
    OUT.mkdir(parents=True, exist_ok=True)
    table.to_csv(OUT / "by_predictor.csv", index=False)
    (OUT / "appendix.md").write_text(appendix(table))
    table["Portfolio Period"] = table["Portfolio Period"].map(
        lambda p: {1.0: "1 (monthly)", 12.0: "12 (annual)"}.get(p, f"other ({p})")
    )
    summary = {"predictors": int(len(doc)), "min_months": MIN_MONTHS, "datasets": {}}
    for label, sub in table.groupby("dataset"):
        d = {"ratio": ratio_summary(sub["post_in_ratio"])}
        for w in WINDOWS:
            hit, n = pass_share(sub, w)
            d[w] = {
                "pos_t2": hit,
                "evaluable": n,
                "share": hit / n,
                "expected_by_chance": expected_by_chance(sub, w),
                "median_mean": float(sub[f"{w}_mean"].median()),
                "share_mean_positive": float((sub[f"{w}_mean"] > 0).mean()),
                "median_months": float(sub[f"{w}_n"].median()),
            }
        d["in_mean_nonpositive"] = int((sub["in_mean"] <= 0).sum())
        summary["datasets"][label] = d
    pivot = table.pivot(index="predictor", columns="dataset")
    summary["op_vs_vw"] = {
        w: {
            "both_pos_t2": int(
                (
                    (pivot[(f"{w}_mean", "op")] > 0)
                    & (pivot[(f"{w}_t", "op")] > 2)
                    & (pivot[(f"{w}_mean", "vw")] > 0)
                    & (pivot[(f"{w}_t", "vw")] > 2)
                ).sum()
            ),
            "corr_of_means": float(pivot[(f"{w}_mean", "op")].corr(pivot[(f"{w}_mean", "vw")])),
        }
        for w in WINDOWS
    }
    for column, name in (
        ("Cat.Data", "by_category"),
        ("Portfolio Period", "by_rebalance"),
        ("Stock Weight", "by_op_weighting"),
    ):
        g = grouped(table, column)
        g.to_csv(OUT / f"{name}.csv", index=False)
        (OUT / f"{name}.md").write_text(group_markdown(g, column, column))
        summary[name] = g.to_dict(orient="records")
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, default=float) + "\n")
    print(json.dumps({k: summary[k] for k in ("datasets", "op_vs_vw")}, indent=2))


if __name__ == "__main__":
    main()
