"""Render the independent-validation tables without any portfolio calculations."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent


def md_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "None."
    header = "| " + " | ".join(frame.columns) + " |"
    rule = "| " + " | ".join("---" for _ in frame.columns) + " |"
    rows = [
        "| " + " | ".join(map(str, values)) + " |"
        for values in frame.itertuples(index=False, name=None)
    ]
    return "\n".join([header, rule, *rows])


def render() -> None:
    summary = pd.read_csv(HERE / "tiingo_validation_summary.csv")
    events = pd.read_csv(HERE / "tiingo_validation_events.csv")
    missing = pd.read_csv(HERE / "tiingo_validation_missing_symbols.csv")
    splits = pd.read_csv(HERE / "tiingo_validation_splits.csv")
    if events.tiingo_status.eq("http_429").any():
        raise RuntimeError("Tiingo returned HTTP 429; report progress instead of final comparison")
    comparable = events.loc[events.tiingo_status == "matched_dates"]
    missing_events = events.loc[events.tiingo_status != "matched_dates"]
    tiingo_internal_max = comparable.tiingo_internal_difference.abs().max()
    formatted = summary.copy()
    for col in ("share_within_1pp", "share_within_5pp"):
        formatted[col] = formatted[col].map(lambda x: f"{100 * x:.1f}%" if pd.notna(x) else "n/a")
    formatted["median_absolute_difference_pp"] = formatted["median_absolute_difference_pp"].map(
        lambda x: ("<0.001" if x < 0.001 else f"{x:.3f}") if pd.notna(x) else "n/a"
    )
    outliers = []
    for event in comparable.itertuples():
        for source, col, dates_col in (
            ("offline", "offline_minus_tiingo", "offline_disagreeing_dates"),
            (
                "EODHD adjusted close",
                "eodhd_adjusted_minus_tiingo",
                "eodhd_adjusted_disagreeing_dates",
            ),
        ):
            difference = getattr(event, col)
            if abs(difference) > 0.10:
                outliers.append(
                    {
                        "bucket": event.bucket,
                        "ticker": event.ticker,
                        "filing_date": event.filing_date,
                        "comparison": source,
                        "difference_pp": f"{100 * difference:+.2f}",
                        "disagreeing_dates (daily difference)": getattr(event, dates_col),
                    }
                )
    missing_formatted = missing[["ticker", "reason", "in_eodhd_delisted_list", "sample_events"]]
    split_formatted = splits[
        [
            "ticker",
            "date",
            "tiingo_split_factor",
            "sample_events_affected",
            "offline_class",
            "offline_factor_step",
            "offline_classified_correctly",
        ]
    ]
    lines = [
        "# Phase 2 independent price validation — locked training sample",
        "",
        "The pre-inspection repository suite finished: "
        "`619 passed, 1 skipped in 97.73s (0:01:37)`. "
        "The 2022-07-01 through 2026-06-30 filing holdout guard ran before price access. "
        "No portfolio return was calculated and no filter or offline classification was changed.",
        "",
        "[Tiingo's official EOD documentation](https://www.tiingo.com/documentation/end-of-day) "
        "defines `close`, `adjClose`, `splitFactor`, and `divCash` and the historical daily-prices "
        "endpoint. [Its split documentation]"
        "(https://www.tiingo.com/documentation/corporate-actions/splits) "
        "defines `splitFactor` as new shares divided by old shares. Requests used only the "
        "Authorization header; request pacing respected 50 per hour. "
        "The raw response cache and request timestamps were deleted after these derived "
        "tables were produced, in line with the free-tier terms.",
        "The Tiingo ticker string was not independently linked to the SEC issuer CIK; "
        "ticker reuse remains a possible source of disagreement and is not filtered here.",
        "",
        f"The seeded file contains **{len(events)} events** "
        f"and **{events.ticker.nunique()} distinct symbols**. "
        f"Of these, **{len(comparable)} events** have exact Tiingo bars at all EODHD session dates "
        f"through the exit; **{len(missing_events)} events** do not. "
        f"**{len(missing)} symbols** return no Tiingo bars or HTTP 404; "
        f"**{int(missing.in_eodhd_delisted_list.sum()) if len(missing) else 0}** of those appear "
        "in the local EODHD delisted list.",
        "",
        "## Return comparison",
        "",
        "Each event enters at the raw open on the first trading day after filing and exits at the "
        "EODHD reference exit close (60 sessions later, or the final available close for an early "
        "terminal event). The same prespecified −30% terminal haircut is applied to all three "
        "sources where applicable. Tiingo total return compounds raw close with `splitFactor` "
        "and `divCash` on each subsequent ex-date. EODHD adjusted-close return scales the entry "
        "raw open by its entry-day adjustment factor. Percent-point comparisons include only "
        "events with exact entry, exit, and interior Tiingo dates; unavailable events are listed "
        "separately and are not counted as agreements. No portfolio aggregation is done.",
        f"As an arithmetic check, Tiingo raw-action returns versus Tiingo's own `adjClose` "
        f"differ by at most {tiingo_internal_max:.3g} in the comparable events.",
        "",
        md_table(
            formatted.rename(
                columns={
                    "bucket": "Dollar-volume bucket",
                    "comparison": "Comparison",
                    "sample_events": "Sample events",
                    "matched_events": "Comparable",
                    "share_within_1pp": "Within 1 pp",
                    "share_within_5pp": "Within 5 pp",
                    "median_absolute_difference_pp": "Median abs diff (pp)",
                    "over_10pp": ">10 pp cases",
                }
            )
        ),
        "",
        "## Every case more than 10 percentage points apart",
        "",
        "The date column lists each symbol-day with a daily return discrepancy above 1 pp "
        "(or the three largest daily differences if none passes that level). Values are the "
        "named source minus Tiingo daily return. EODHD adjusted-close differences can also "
        "arise from adjustment-factor changes.",
        "",
        md_table(pd.DataFrame(outliers)),
        "",
        "## Tiingo split records in sampled event windows",
        "",
        "The split census covers each sampled event's requested 30 EODHD sessions before "
        "entry through 70 sessions after entry, limited by available local history. A split "
        "is counted correctly only when the offline day was labelled `split` and its factor "
        "step was within 2% of Tiingo's `splitFactor`. Overlapping sampled windows count once "
        "per symbol-day.",
        "",
        md_table(split_formatted),
        "",
        "## Symbols without Tiingo bars",
        "",
        md_table(missing_formatted),
        "",
        "## Other event-level coverage failures",
        "",
        md_table(
            missing_events.loc[
                ~missing_events.tiingo_status.isin(["empty_series", "http_404"]),
                ["bucket", "ticker", "filing_date", "entry_date", "exit_date", "tiingo_status"],
            ]
        ),
        "",
        "Full derived event-level values and disagreement dates are in "
        "[tiingo_validation_events.csv](tiingo_validation_events.csv). No raw Tiingo daily "
        "price series is retained.",
        "",
    ]
    (HERE / "tiingo_validation_report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    render()
