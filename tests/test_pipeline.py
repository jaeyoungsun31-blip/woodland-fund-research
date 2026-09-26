"""End-to-end pipeline wiring test with mocked data sources.

Network is often unavailable where tests run; this verifies the
ingest -> store -> matrix -> integrity -> backtest chain without it.
The real-data run is `python scripts/ingest.py` (needs internet).
"""

import numpy as np
import pandas as pd
import pytest

from woodland import backtest, data, metrics


def fake_yahoo(n_days=1500, seed=3, div_bps=25):
    """Synthetic OHLCV with a realistic quarterly-dividend adjustment factor."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2019-01-02", periods=n_days)
    out = {}
    for t, mu in [("SPY", 0.0005), ("IEF", 0.0001)]:
        close = 100 * np.cumprod(1 + rng.normal(mu, 0.01, n_days))
        # cumulative dividend-discount factor: steps up on ex-div days, ends at 1.0
        pays = np.zeros(n_days)
        pays[::63] = div_bps / 1e4
        factor = np.cumprod(1 - pays[::-1])[::-1]
        factor = factor / factor[-1]
        out[t] = pd.DataFrame({
            "open": close * (1 + rng.normal(0, 0.002, n_days)),
            "high": close * 1.005, "low": close * 0.995,
            "close": close, "volume": rng.integers(1e6, 5e6, n_days),
            "adj_close": close * factor,
        }, index=idx)
    return out


def test_ingest_to_backtest_chain(tmp_path, monkeypatch):
    market = fake_yahoo()
    monkeypatch.setattr(data, "fetch_yahoo", lambda t, start: market[t])

    for t in ["SPY", "IEF"]:
        res = data.ingest_ticker(t, "2019-01-01", tmp_path)
        assert res.provenance["adjustment"]["verdict"] == "ok", res.provenance
        assert res.ok

    prices = data.build_matrix(["SPY", "IEF"], tmp_path)
    assert prices.shape == (1500, 2)

    report = data.integrity_report(prices)
    assert (report["flag"] == "ok").all(), report.to_string()

    res = backtest.fixed_mix(prices, {"SPY": 0.6, "IEF": 0.4}, cost_bps=5.0)
    summary = res.summary()
    assert np.isfinite(summary["cagr"])
    assert summary["ann_turnover"] > 0

    sub = metrics.by_subperiod(res.returns)
    assert len(sub) >= 1


def test_single_source_ingest_is_never_reported_as_verified(tmp_path, monkeypatch):
    """A single-source ingest must say NO SECOND SOURCE, never 'ok'.

    This is the guard against the cross-check quietly becoming a no-op while
    still printing a reassuring verdict (DESIGN.md §5).
    """
    market = fake_yahoo()
    monkeypatch.setattr(data, "fetch_yahoo", lambda t, start: market[t])

    res = data.ingest_ticker("SPY", "2019-01-01", tmp_path, crosscheck_source=None)
    assert res.provenance["crosscheck"]["verdict"] == "NO SECOND SOURCE"
    assert res.provenance["crosscheck_source"] is None

    prov = data.read_provenance(tmp_path)  # written by the ingest script, not here
    assert prov == {}
    data.write_provenance({"SPY": res.provenance}, tmp_path)
    assert data.read_provenance(tmp_path)["SPY"]["crosscheck"]["verdict"] == "NO SECOND SOURCE"


def test_crosscheck_source_failure_is_recorded_not_swallowed(tmp_path, monkeypatch):
    market = fake_yahoo()
    monkeypatch.setattr(data, "fetch_yahoo", lambda t, start: market[t])
    monkeypatch.setitem(data.SOURCES, "stooq",
                        lambda t, start: (_ for _ in ()).throw(RuntimeError("404 blocked")))

    res = data.ingest_ticker("SPY", "2019-01-01", tmp_path, crosscheck_source="stooq")
    assert res.provenance["crosscheck"]["verdict"] == "SOURCE UNAVAILABLE"
    assert "404" in res.provenance["crosscheck"]["error"]
    assert not res.ok


def test_primary_fetch_failure_leaves_the_existing_parquet_unchanged(tmp_path, monkeypatch):
    """A failed replacement must not overwrite a prior ticker store entry."""
    existing = fake_yahoo()["SPY"]
    existing.to_parquet(tmp_path / "SPY.parquet")
    monkeypatch.setattr(
        data,
        "fetch_yahoo",
        lambda ticker, start: (_ for _ in ()).throw(RuntimeError("temporary outage")),
    )

    with pytest.raises(RuntimeError, match="temporary outage"):
        data.ingest_ticker("SPY", "2019-01-01", tmp_path)

    pd.testing.assert_frame_equal(data.load_ticker("SPY", tmp_path), existing, check_freq=False)


def test_check_adjustment_catches_broken_factor():
    market = fake_yahoo()
    good = market["SPY"]
    assert data.check_adjustment(good)["verdict"] == "ok"

    # a spliced/stale adjustment series: factor runs backwards
    bad = good.copy()
    bad["adj_close"] = good["close"] * np.linspace(1.0, 0.8, len(good))
    assert data.check_adjustment(bad)["verdict"].startswith("INVESTIGATE")

    # adjusted series that never converges to the raw close on the last bar
    stale = good.copy()
    stale["adj_close"] = good["adj_close"] * 0.9
    assert "terminal factor" in data.check_adjustment(stale)["verdict"]


def test_crosscheck_sources_agrees_and_disagrees():
    idx = pd.bdate_range("2020-01-01", periods=600)
    rng = np.random.default_rng(11)
    a = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, 600)), index=idx)

    # same prices with sub-tolerance rounding noise -> ok
    b = (a * (1 + rng.normal(0, 1e-5, 600))).round(6)
    assert data.crosscheck_sources(a, b)["verdict"] == "ok"

    # an independent series -> INVESTIGATE
    c = pd.Series(100 * np.cumprod(1 + rng.normal(0, 0.01, 600)), index=idx)
    assert data.crosscheck_sources(a, c)["verdict"] == "INVESTIGATE"

    # too little overlap to conclude anything
    report = data.crosscheck_sources(a.iloc[:100], b.iloc[:100])
    assert report["verdict"] == "insufficient overlap"


def test_crosscheck_monitors_50bps_but_only_fails_above_2pct():
    idx = pd.bdate_range("2020-01-01", periods=600)
    primary = pd.Series(100.0, index=idx)

    monitored = primary.copy()
    monitored.iloc[300:] *= 1.01
    report = data.crosscheck_sources(primary, monitored)
    assert report["n_days_gt_monitor"] == 1
    assert report["n_days_gt_fail"] == 0
    assert report["verdict"] == "ok"

    failed = primary.copy()
    failed.iloc[300:] *= 1.03
    report = data.crosscheck_sources(primary, failed)
    assert report["n_days_gt_fail"] == 1
    assert report["verdict"] == "INVESTIGATE"


def test_integrity_report_flags_bad_data(tmp_path):
    idx = pd.bdate_range("2024-01-01", periods=300)
    good = pd.Series(np.linspace(100, 120, 300), index=idx)
    jumpy = good.copy()
    jumpy.iloc[150] *= 1.5  # >20% move
    short = good.iloc[-100:]                               # < 3 years
    prices = pd.DataFrame({"GOOD": good, "JMP": jumpy, "SHRT": short})
    rep = data.integrity_report(prices)
    assert "JUMPS" in rep.loc["JMP", "flag"]
    assert "SHORT HISTORY" in rep.loc["SHRT", "flag"]
    assert "SHORT HISTORY" in rep.loc["GOOD", "flag"]      # 300 bdays < 3y too


def test_integrity_report_reports_a_stale_terminal_bar_without_changing_flags():
    idx = pd.bdate_range("2024-01-01", periods=400)
    base = pd.Series(np.linspace(100, 130, 400), index=idx)
    prices = pd.DataFrame({"A": base, "B": base, "STALE": base.iloc[:-1]})

    report = data.integrity_report(prices)

    assert report.loc["A", "last_bar_consensus"] == str(idx[-1].date())
    assert report.loc["A", "freshness"] == "CURRENT"
    assert report.loc["STALE", "freshness"] == "STALE VS CONSENSUS"
    assert "STALE" not in report.loc["STALE", "flag"]


def test_calendar_check_finds_a_feed_hole():
    """One ticker missing a bar the rest of the universe traded must be flagged.

    The per-ticker gap check cannot see this: a single absent weekday leaves a
    4-day gap, shorter than a legitimate holiday weekend. Only the
    cross-sectional check catches it.
    """
    idx = pd.bdate_range("2024-01-01", periods=400)
    base = pd.Series(np.linspace(100, 130, 400), index=idx)
    prices = pd.DataFrame({t: base * (1 + i / 100) for i, t in enumerate("ABCDE")})
    assert data.calendar_report(prices).empty

    hole = idx[200]
    prices.loc[hole, ["A", "B", "C", "D"]] = np.nan       # 4 of 5 absent
    cal = data.calendar_report(prices)
    assert list(cal.index) == [hole.date()]
    assert cal.loc[hole.date(), "n_present"] == 1
    assert set(cal.loc[hole.date(), "missing"].split(",")) == {"A", "B", "C", "D"}

    # the old per-ticker gap heuristic is blind to it
    gaps = prices["A"].dropna().index.to_series().diff().dt.days
    assert gaps.max() <= 4


def test_missing_bars_counts_only_absences_on_consensus_days():
    idx = pd.bdate_range("2024-01-01", periods=400)
    base = pd.Series(np.linspace(100, 130, 400), index=idx)
    prices = pd.DataFrame({t: base * (1 + i / 100) for i, t in enumerate("ABCDE")})
    prices.loc[idx[200], "A"] = np.nan                     # 1 of 5 absent -> A's hole
    prices.loc[: idx[50], "E"] = np.nan                    # E simply lists later

    holes = data.missing_bars(prices)
    assert holes["A"] == 1
    assert holes["E"] == 0                                 # not yet alive != missing
    assert data.integrity_report(prices).loc["A", "flag"].count("MISSING BARS") == 1


def test_drop_suspect_dates_excludes_rather_than_fabricates():
    idx = pd.bdate_range("2024-01-01", periods=400)
    base = pd.Series(np.linspace(100, 130, 400), index=idx)
    prices = pd.DataFrame({t: base * (1 + i / 100) for i, t in enumerate("ABCDE")})
    hole = idx[200]
    prices.loc[hole, ["A", "B", "C", "D"]] = np.nan

    clean, dropped = data.drop_suspect_dates(prices)
    assert list(dropped) == [hole]
    assert hole not in clean.index
    assert len(clean) == len(prices) - 1
    assert clean.notna().all().all()          # no NaN survived, none invented
    assert prices.loc[hole].isna().sum() == 4  # source matrix untouched
