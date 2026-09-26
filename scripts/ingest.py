"""Refresh the data store: download, check, integrity-report, record provenance.

Every ticker's check results are written to data/_provenance.json so the
state of the data layer is inspectable without re-downloading.

Usage:  python scripts/ingest.py [--tickers SPY,QQQ] [--report-only]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from woodland import data
from woodland.config import ROOT, all_tickers, load_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("ingest")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", help="comma-separated subset; default = full universe")
    ap.add_argument("--report-only", action="store_true",
                    help="skip downloads; re-run checks on the existing store")
    args = ap.parse_args()

    cfg = load_config()
    # ``store`` is the immutable research artifact.  Ingest must only update
    # the separate live working store, even when invoked by the cycle.
    store = ROOT / cfg["data"].get("live_store", cfg["data"]["store"])
    tickers = args.tickers.split(",") if args.tickers else all_tickers(cfg)
    xsource = cfg["data"].get("crosscheck_source")
    fail_tol = cfg["data"]["crosscheck_fail_tolerance"]
    monitor_tol = cfg["data"]["crosscheck_monitor_tolerance"]

    failures: list[tuple[str, object]] = []
    unchecked: list[str] = []
    prov = data.read_provenance(store)

    if not args.report_only:
        for t in tickers:
            try:
                res = data.ingest_ticker(t, cfg["data"]["start"], store,
                                         crosscheck_source=xsource,
                                         fail_tolerance=fail_tol,
                                         monitor_tolerance=monitor_tol)
                prov[t] = res.provenance
                adj = res.provenance["adjustment"]["verdict"]
                xchk = res.provenance["crosscheck"]["verdict"]
                log.info("%-5s %6d rows  %s..%s  adjustment=%s  crosscheck=%s",
                         t, res.provenance["rows"], res.provenance["first"],
                         res.provenance["last"], adj, xchk)
                if adj != "ok":
                    failures.append((t, res.provenance["adjustment"]))
                if xchk != "ok":
                    unchecked.append(t)
            except Exception as e:
                log.error("%-5s FAILED: %s", t, e)
                failures.append((t, str(e)))
        data.write_provenance(prov, store)

    monitored_rows = []
    total_monitored = 0
    total_comparisons = 0
    for t in tickers:
        xcheck = prov.get(t, {}).get("crosscheck", {})
        if "n_days_gt_monitor" not in xcheck:
            continue
        count = int(xcheck["n_days_gt_monitor"])
        comparisons = max(int(xcheck.get("overlap_days", 0)) - 1, 0)
        monitored_rows.append((t, count, comparisons, xcheck.get("n_days_gt_fail", 0)))
        total_monitored += count
        total_comparisons += comparisons

    if monitored_rows:
        print("\n=== cross-source return-difference monitor ===")
        print(f"  monitor >{monitor_tol:.2%}; hard fail >{fail_tol:.2%}")
        for ticker, count, comparisons, hard_failures in monitored_rows:
            print(f"  {ticker:5s} {count:4d} / {comparisons:5d} monitored; "
                  f"hard failures={hard_failures}")
        print(f"  TOTAL {total_monitored} / {total_comparisons} monitored "
              "(recorded baseline: 484 / 122905)")

    stored = [t for t in tickers if (store / f"{t}.parquet").exists()]
    if stored:
        prices = data.build_matrix(stored, store, research=False)
        report = data.integrity_report(prices)
        print("\n=== integrity report (adj_close) ===")
        print(report.to_string())
        stale = report[report["freshness"] == "STALE VS CONSENSUS"]
        if len(stale):
            consensus = report["last_bar_consensus"].iloc[0]
            print("\n!!! STALE TICKER PARQUET(S) DETECTED !!!")
            print(f"  store-wide last-bar consensus: {consensus}")
            print("  These tickers retained older data after a failed fetch:")
            print("  " + ", ".join(stale.index.tolist()))
            print("  Report only: this does not alter the ingest verdict.")

        cal = data.calendar_report(prices)
        print("\n=== calendar check (cross-sectional) ===")
        if cal.empty:
            print("  clean: every date is reported by >=80% of live tickers")
        else:
            print(f"  {len(cal)} suspect date(s) — some live tickers have no bar:")
            print(cal.to_string())
            print("  These are feed holes, not market events. Do NOT forward-fill;")
            print("  a fabricated bar is worse than a known gap.")
            failures.append(("calendar", f"{len(cal)} suspect date(s)"))
    else:
        print("\nno data in store — every download failed?")
        return 1

    if unchecked:
        print("\n=== INDEPENDENT CROSS-CHECK NOT CLEAN ===")
        print(f"  crosscheck_source = {xsource!r}; {len(unchecked)} ticker(s) did not")
        print("  receive an 'ok' cross-check verdict. The primary store remains usable,")
        print("  but the source-verification caveat cannot be lifted.")

    if failures:
        print("\n=== NEEDS ATTENTION ===")
        for t, info in failures:
            print(f"  {t}: {info}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
