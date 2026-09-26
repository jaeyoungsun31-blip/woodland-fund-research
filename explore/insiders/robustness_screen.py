"""Training-only EODHD adjusted-close robustness screens for insider clusters."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import replace
from typing import cast

import numpy as np
import pandas as pd
from bias_corrections import (
    FACTOR_NAMES,
    build_trades,
    hac_fit,
    load_factors,
    pre_entry_screen,
)
from first_returns import (
    BUCKETS,
    HERE,
    REPO,
    STORE,
    Trade,
    cluster_starts,
    load_locked_inputs,
    simulate,
    verify_transaction_prices,
)
from holdout import require_training_events

PINNED_CASH_SHA256 = "ae34413413be72b85fcddfcf3a384ea6a5b66097b2887726dae4380239b763d7"


def gross_event_return(trade: Trade) -> float:
    return float(trade.closes[-1] * (1 + trade.delisting_return) / trade.opens[0] - 1)


def winsorize_trade(trade: Trade, lower: float, upper: float) -> Trade:
    """Clip the full-window gross return through a final-day mark only."""
    clipped = float(np.clip(gross_event_return(trade), lower, upper))
    closes = trade.closes.copy()
    closes[-1] = trade.opens[0] * (1 + clipped) / (1 + trade.delisting_return)
    result = replace(trade, closes=closes)
    if not np.isclose(gross_event_return(result), clipped, atol=1e-12):
        raise RuntimeError("Winsorized terminal mark did not produce the clipped return")
    return result


def median_monthly(trades: list[Trade], calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """Median within-month return of positions active during that month."""
    rows: dict[pd.Period, list[tuple[float, float]]] = defaultdict(list)
    for trade in trades:
        dates = calendar[trade.entry_idx : trade.exit_idx + 1]
        if len(dates) != len(trade.closes) or len(dates) != len(trade.opens):
            raise RuntimeError("Trade marks do not match the reference calendar")
        cost = trade.spread + 0.0005
        for month in dates.to_period("M").unique():
            positions = np.flatnonzero(dates.to_period("M") == month)
            first, last = int(positions[0]), int(positions[-1])
            entered = first == 0
            exited = last == len(dates) - 1
            start = float(trade.opens[0] if entered else trade.closes[first - 1])
            end = float(trade.closes[last])
            if exited:
                end *= 1 + trade.delisting_return
            gross = end / start - 1
            net = (1 + gross) * ((1 - cost) if entered else 1) * ((1 - cost) if exited else 1) - 1
            rows[month].append((gross, net))
    return pd.DataFrame(
        {
            "month": [month.to_timestamp("M") for month in sorted(rows)],
            "gross": [
                float(np.median([value[0] for value in rows[month]])) for month in sorted(rows)
            ],
            "net": [
                float(np.median([value[1] for value in rows[month]])) for month in sorted(rows)
            ],
            "active_positions": [len(rows[month]) for month in sorted(rows)],
        }
    )


def summarize(
    monthly: pd.DataFrame,
    trades: list[Trade],
    iwm_monthly: pd.Series,
    french_monthly: pd.DataFrame,
    bucket: str,
    variant: str,
) -> dict[str, object]:
    frame = monthly.set_index("month").join(iwm_monthly.rename("iwm"), how="inner")
    frame = frame.join(french_monthly[["RF", *FACTOR_NAMES]], how="inner").dropna()
    if frame.empty:
        raise RuntimeError(f"No aligned monthly observations for {bucket}/{variant}")
    fit = hac_fit((frame.net - frame.RF).to_numpy(float), frame[list(FACTOR_NAMES)].to_numpy(float))
    return {
        "variant": variant,
        "bucket": bucket,
        "clusters": len(trades),
        "months": len(frame),
        "terminal_events": sum(trade.delisting_return < 0 for trade in trades),
        "gross_excess_iwm": float((frame.gross - frame.iwm).mean()),
        "net_excess_iwm": float((frame.net - frame.iwm).mean()),
        "alpha_monthly": float(fit["coefficient"][0]),
        "alpha_t_hac3": float(fit["tstat"][0]),
        "residual_std_monthly": float(fit["residual_std"]),
        "worst_net_month": float(frame.net.min()),
        "worst_net_month_date": pd.Timestamp(frame.net.idxmin()).date().isoformat(),
    }


def main() -> None:
    # The guard runs before opening any price or factor file.
    events, transactions = load_locked_inputs()
    require_training_events(events.filing_date)
    require_training_events(transactions.filing_date)
    french_monthly, _, _ = load_factors()
    spy = pd.read_parquet(REPO / "data/SPY.parquet")
    calendar = pd.DatetimeIndex(pd.to_datetime(spy.index)).sort_values().unique()
    iwm = pd.read_parquet(REPO / "data/IWM.parquet").sort_index()
    eligible_pre, _ = pre_entry_screen(events, calendar)
    eligible, _ = verify_transaction_prices(eligible_pre, transactions)
    starts = cluster_starts(eligible)
    require_training_events(starts.filing_date)
    delisted = {item["Code"] for item in json.loads((STORE / "delisted-symbols.json").read_text())}
    trades, _, _, _ = build_trades(starts, 60, calendar, delisted, iwm)
    if len(trades) != 10261:
        raise RuntimeError(f"Unexpected primary executed-cluster count: {len(trades)}")
    cash_path = REPO / "data/fama_french_factors_daily.parquet"
    if hashlib.sha256(cash_path.read_bytes()).hexdigest() != PINNED_CASH_SHA256:
        raise RuntimeError("Pinned CASH index hash mismatch")
    cash = pd.read_parquet(cash_path).CASH
    iwm_monthly = iwm.adj_close.resample("ME").last().pct_change()
    gross_returns = np.array([gross_event_return(trade) for trade in trades])
    lower, upper = np.quantile(gross_returns, [0.01, 0.99], method="linear")
    winsorized = [winsorize_trade(trade, float(lower), float(upper)) for trade in trades]
    summary_rows = []
    monthly_rows = []
    for bucket in BUCKETS:
        original = [trade for trade in trades if trade.bucket == bucket]
        clipped = [trade for trade in winsorized if trade.bucket == bucket]
        for variant, monthly in (
            ("original_eodhd_adjusted", simulate(original, calendar, cash)),
            ("pooled_1_99_winsor", simulate(clipped, calendar, cash)),
            ("median_active_positions", median_monthly(original, calendar)),
        ):
            summary_rows.append(
                summarize(monthly, original, iwm_monthly, french_monthly, bucket, variant)
            )
            monthly_rows.append(monthly.assign(bucket=bucket, variant=variant))
    summary = pd.DataFrame(summary_rows)
    baseline = pd.read_csv(HERE / "survival_correction_summary.csv")
    original_rows = summary.loc[summary.variant == "original_eodhd_adjusted"].set_index("bucket")
    old_rows = baseline.set_index("bucket")
    for bucket in BUCKETS:
        for current, prior in (
            ("clusters", "clusters"),
            ("gross_excess_iwm", "gross_excess_iwm"),
            ("net_excess_iwm", "net_excess_iwm"),
        ):
            if not np.isclose(
                cast(float, original_rows.at[bucket, current]),
                cast(float, old_rows.at[bucket, prior]),
                atol=1e-12,
            ):
                raise RuntimeError(f"Primary EODHD baseline did not reproduce: {bucket}/{current}")
    summary.to_csv(HERE / "robustness_screen_summary.csv", index=False)
    pd.concat(monthly_rows, ignore_index=True).to_csv(
        HERE / "robustness_screen_monthly.csv", index=False
    )
    (HERE / "robustness_screen_metadata.json").write_text(
        json.dumps(
            {
                "training_events": len(trades),
                "winsor_lower": float(lower),
                "winsor_upper": float(upper),
                "winsor_clipped_low": int((gross_returns < lower).sum()),
                "winsor_clipped_high": int((gross_returns > upper).sum()),
                "return_source": "EODHD per-symbol adjusted_close",
                "holdout_guard": "2012-01-01 through 2022-06-30 filings only",
            },
            indent=2,
        )
        + "\n"
    )
    print(summary.to_string(index=False))
    print(f"winsorization_cutoffs=({lower:.8f},{upper:.8f})")


if __name__ == "__main__":
    main()
