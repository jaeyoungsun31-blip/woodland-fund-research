"""Preregistered v16 on a sparse observed-return panel; refusals are outcomes."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from woodland import backtest, cash, data, metrics, stats
from woodland.config import load_config
from woodland.harness import deflated
from woodland.harness.ledger import TrialsLedger
from woodland.harness.splits import check_embargo_covers_lookback, make_splits
from woodland.signals import costaware as model
from woodland.snapshot import etf_snapshot, file_hash, verify_pinned_input

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/xsmom-v16-panel/pinned-run"
PANEL = ROOT / "reports/security-resolver/2026-09-07-constituent-panel/panel-returns.parquet"
COSTS: tuple[float, ...] = (0.0, 5.0, 10.0, 25.0, 50.0)
REPORTING_BLOCK = {
    "refused_constituents": 213,
    "refused_symbol_years": 1574,
    "excluded_defects": ["CTX", "DF", "IGT", "COG"],
    "substitutions": {"SYMC": "GEN", "NLOK": "GEN", "WIN": "WINMQ", "KRFT": "KHC", "MMC": "MRSH"},
    "no_usable_bars": ["FCPT"],
    "a2": "SIGNED convention; treatment not applied to this panel. "
    "No imputed terminal returns or Case 2 adverse bound.",
}


def frozen_research_store(root: Path = ROOT) -> Path:
    """Resolve the planning-declared immutable ETF research store."""
    configured = Path(str(load_config(root / "config" / "universe.yaml")["data"]["store"]))
    return configured if configured.is_absolute() else root / configured


def _write_ledger_batch(
    study: str, records: list[dict[str, Any]], *, status: str
) -> dict[str, int]:
    """Append one arm's terminal ledger batch without touching prior rows."""
    with TrialsLedger(ROOT / "journal/trials.db") as ledger:
        for record in records:
            ledger.record(
                study,
                record["config"],
                status=status,
                metrics=record["metrics"] if status == "evaluated" else None,
                cost_bps=record["cost_bps"],
                split_index=record["split_index"],
                window=record["window"],
                split_scheme=record["split_scheme"],
                notes=record["notes"],
            )
        return {
            "trials": ledger.n_trials(study, distinct=False),
            "distinct_cells": ledger.n_trials(study),
        }


def commit_completed_ledger(study: str, records: list[dict[str, Any]]) -> dict[str, int]:
    """Append a completed arm only after its staged directory is promoted."""
    return _write_ledger_batch(study, records, status="evaluated")


def eligibility(panel: pd.DataFrame, arm: str) -> tuple[pd.DataFrame, dict]:
    base = panel.notna()
    allowed = base.copy()
    flag_mask = base & False
    crosscheck_path = ROOT / "reports/security-resolver/2026-09-07-tiingo-crosscheck/crosscheck.csv"
    verify_pinned_input(crosscheck_path)
    compared = pd.read_csv(crosscheck_path)
    fail = compared.loc[
        (compared.status == "compared") & (compared.n_days_gt_fail.fillna(0) > 0), "symbol"
    ]
    events_path = (
        ROOT
        / "reports/security-resolver/2026-09-07-missed-event-screen/missed-event-candidates.csv"
    )
    verify_pinned_input(events_path)
    events = pd.read_csv(events_path)
    events = events[events.nearest_split_ratio.notna()]
    assert len(fail) == 68 and len(events) == 143
    calendar_path = ROOT / "data/SPY.parquet"
    verify_pinned_input(calendar_path)
    calendar = pd.DatetimeIndex(pd.read_parquet(calendar_path).index)
    for row in events.itertuples():
        if row.symbol not in panel:
            continue  # CTX is already explicitly excluded by panel construction.
        start = pd.Timestamp(str(row.date))
        pos = int(calendar.get_indexer(pd.DatetimeIndex([start]))[0])
        if pos < 0:
            raise ValueError(f"Flag date absent from trading calendar: {row.symbol} {start}")
        end = calendar[min(pos + 252, len(calendar) - 1)]
        flag_mask.loc[(panel.index >= start) & (panel.index <= end), str(row.symbol)] = True
    if arm == "B":
        allowed[allowed.columns.intersection(fail.tolist()).tolist()] = False
        allowed &= ~flag_mask
    return allowed, dict(
        candidate_days=143,
        fail_symbols=fail.tolist(),
        flag_only_membership_symbol_days=int((flag_mask & base).sum().sum()),
        total_ineligible_symbol_days=int((base & ~allowed).sum().sum()),
    )


def declared_membership_eligibility(
    membership: pd.DataFrame,
) -> Any:
    """Return the signed arm-panel membership eligibility function.

    Short gaps are filled when the signed constituent-panel artifacts are
    constructed.  This function deliberately applies only that frozen
    membership mask; it does not recreate or extend the fill policy.
    """

    def _eligibility(panel: pd.DataFrame, arm: str) -> tuple[pd.DataFrame, dict[str, int]]:
        mask = membership.reindex(index=panel.index, columns=panel.columns, fill_value=False)
        return mask, {"declared_arm_panel": 1}

    return _eligibility


def momentum_gate_pair(
    runs: dict[tuple[str, float], pd.Series], cost_bps: float
) -> tuple[pd.Series, pd.Series]:
    """Return the penalized and momentum return series at one declared cost."""
    return runs["penalized", cost_bps], runs["momentum", cost_bps]


def execute(
    panel: pd.DataFrame,
    arm: str,
    provenance: dict,
    *,
    output_path: Path | None = None,
    study_id: str | None = None,
    defer_success_ledger: bool = False,
    dsr_n_trials: int | None = None,
    momentum_gate_cost_bps: float = 25.0,
    positive_gate: bool = False,
    expected_fold_count: int = 22,
) -> dict:
    """Run one arm, optionally writing it to a caller-owned staging directory."""
    verify_pinned_input(PANEL)
    allowed, mask_info = eligibility(panel, arm)
    index = pd.DatetimeIndex(panel.index)
    formation_days = set(index.to_series().groupby(index.to_period("M")).max())
    x = model.features(panel, allowed)
    y = model.labels(panel)
    folds = make_splits(index, train_years=5, validate_years=1, step_years=1, embargo_days=252)
    check_embargo_covers_lookback(folds, index, 252)
    if len(folds) != expected_fold_count:
        raise ValueError(
            f"unexpected fold count: expected {expected_fold_count}, got {len(folds)}"
        )
    oos = index[index >= folds[0].validate_index(index)[0]]
    assert len(oos) == 5234 and str(oos[-1].date()) == "2026-06-30"
    rf, rf_provenance = cash.align_risk_free(cash.load_risk_free_daily(ROOT / "data"), index)
    daily = pd.DataFrame(
        {
            "membership_names": panel.notna().sum(axis=1),
            "remaining_membership_eligible": allowed.sum(axis=1),
            "excluded_names": (panel.notna() & ~allowed).sum(axis=1),
            "complete_feature_eligible": np.isfinite(x).all(axis=2).sum(axis=1),
        }
    )
    daily["excluded_fraction"] = daily.excluded_names / daily.membership_names
    daily["portfolio_window"] = daily.index.isin(oos)
    path = output_path if output_path is not None else OUT / arm
    path.mkdir(exist_ok=False)
    daily.to_csv(path / "eligibility-by-day.csv")
    study = study_id or f"xsmom-v16-panel-{arm}-20260907"
    with TrialsLedger(ROOT / "journal/trials.db") as ledger:
        if ledger.has_completed_study(study):
            raise ValueError("Study ID already has a completed arm; refusing duplicate run")
    staged: list[dict[str, Any]] = []
    selected = []
    coefficients = []
    stitched = {
        name: pd.DataFrame(np.nan, index=index, columns=panel.columns)
        for name in ["penalized", "ridge", "momentum", "equal"]
    }
    outcome = dict(
        arm=arm,
        status="running",
        snapshot=provenance,
        reporting_block=REPORTING_BLOCK,
        mask=mask_info,
        minimum_membership_eligible=int(daily.remaining_membership_eligible.min()),
        minimum_feature_eligible_on_oos=int(daily.loc[oos, "complete_feature_eligible"].min()),
        portfolio_days_over_10pct_excluded=int((daily.loc[oos, "excluded_fraction"] > 0.1).sum()),
        portfolio_days=len(oos),
        risk_free=rf_provenance,
        C1=None,
        C2=None,
        C3=None,
    )
    failure: dict[str, Any] | None = None
    for fold in folds:
        train = fold.train_index(index)
        valid = fold.validate_index(index)
        ti = index.get_indexer(train)
        train_y = y[ti].copy()
        train_y[-21:] = np.nan
        sufficient = model.sufficient_statistics(x[ti], train_y)
        scores = {}
        fitted = {}
        for alpha, lam in model.GRID:
            record: dict[str, Any] = dict(
                config={"alpha": alpha, "lambda": lam},
                split_index=fold.i,
                window=f"train {train[0].date()}..{train[-1].date()}",
                split_scheme={
                    "train_years": 5,
                    "validate_years": 1,
                    "step_years": 1,
                    "embargo_days": 252,
                    "n_splits": 22,
                },
                cost_bps=5.0,
                status="error",
                notes="",
                metrics=None,
            )
            try:
                b = model.fit(sufficient, alpha, lam)
                coefficients.append(
                    dict(
                        split=fold.i,
                        alpha=alpha,
                        lam=lam,
                        b=b.tolist(),
                        training_observations=sufficient[3],
                    )
                )
                t = model.targets(
                    panel.loc[train], x[ti], allowed.loc[train], b, formation_days=formation_days
                )
                result = backtest.run_returns(
                    panel.loc[train],
                    t,
                    cost_bps=5.0,
                    risk_free=rf.loc[train],
                    eligibility=allowed.loc[train],
                )
                measured = metrics.summarize(
                    result.returns, result.turnover, rf_daily=rf.loc[train]
                )
                score = measured["sharpe_rf"]
                if not np.isfinite(score):
                    raise ValueError("nonfinite train excess Sharpe")
                scores[(alpha, lam)] = score
                fitted[(alpha, lam)] = b
                record.update(status="evaluated", metrics={**measured, "n_obs": len(train)})
            except (ValueError, np.linalg.LinAlgError) as error:
                record["notes"] = str(error)
            staged.append(record)
        # A refusal is not a way to cherry-pick a surviving subset of the grid.
        errors = [r for r in staged if r["split_index"] == fold.i and r["status"] == "error"]
        if errors:
            failure = dict(
                phase="training_cost_evaluation",
                fold=fold.i,
                reason="A registered cell is unpriceable or failed; no subset grid substituted.",
                failures=errors,
            )
            break
        for name, predicate in [("penalized", lambda c: c[1] > 0), ("ridge", lambda c: c[1] == 0)]:
            best = max((c for c in scores if predicate(c)), key=lambda c: scores[c])
            selected.append(
                dict(split=fold.i, arm=name, alpha=best[0], lam=best[1], train_score=scores[best])
            )
            # Full prefix avoids treating a partial fold month as a new month-end.
            prefix = index[index <= valid[-1]]
            t = model.targets(
                panel.loc[prefix],
                x[: len(prefix)],
                allowed.loc[prefix],
                fitted[best],
                formation_days=formation_days,
            )
            stitched[name].loc[valid] = t.loc[valid]
        for kind in ["momentum", "equal"]:
            prefix = index[index <= valid[-1]]
            t = model.targets(
                panel.loc[prefix],
                x[: len(prefix)],
                allowed.loc[prefix],
                None,
                kind=kind,
                formation_days=formation_days,
            )
            stitched[kind].loc[valid] = t.loc[valid]
    verify_pinned_input(PANEL)
    for record in staged:
        record["notes"] += (
            f"; as_of={provenance['as_of']}; ETF hash={provenance['sha256']}"
            f"; panel hash={file_hash(PANEL)}"
        )
    (path / "trials.json").write_text(json.dumps(staged, indent=2, default=str))
    (path / "coefficients.json").write_text(json.dumps(coefficients, indent=2))
    (path / "selections.json").write_text(json.dumps(selected, indent=2))
    if failure:
        outcome.update(
            status="refused",
            failure=failure,
            performance=None,
            dsr=None,
            unrun_folds=22 - 1 - failure["fold"],
        )
    else:
        runs = {}
        summaries = []
        try:
            for name, t in stitched.items():
                for cost in COSTS:
                    result = backtest.run_returns(
                        panel, t, cost_bps=cost, risk_free=rf, eligibility=allowed
                    )
                    r = result.returns.loc[oos]
                    turn = result.turnover.loc[oos]
                    runs[(name, cost)] = r
                    summaries.append(
                        dict(
                            strategy=name,
                            cost_bps=cost,
                            **metrics.summarize(r, turn, rf_daily=rf.loc[oos]),
                        )
                    )
                    metrics.by_subperiod(r).to_csv(path / f"{name}-{cost:g}-subperiods.csv")
                    pd.DataFrame({"return": r, "turnover": turn}).to_csv(
                        path / f"{name}-{cost:g}-returns.csv"
                    )
            c1 = stats.bootstrap_sharpe_difference(
                runs["penalized", 10.0], runs["ridge", 10.0], rf_daily=rf.loc[oos], seed=0
            )
            penalized_momentum, naive_momentum = momentum_gate_pair(
                runs, momentum_gate_cost_bps
            )
            c2 = stats.bootstrap_sharpe_difference(
                penalized_momentum,
                naive_momentum,
                rf_daily=rf.loc[oos],
                seed=0,
            )
            dsr_result = deflated.deflated_sharpe(
                runs["penalized", 10.0] - rf.loc[oos],
                n_trials=dsr_n_trials if dsr_n_trials is not None else len(staged),
                trial_sharpes=np.array([r["metrics"]["sharpe_rf"] for r in staged]),
            )
            outcome.update(
                status="completed",
                C1=c1.ci_low > 0,
                C2=c2.ci_low > 0,
                C3=c1.ci_low > 0 and c2.ci_low > 0,
                inference={"C1": asdict(c1), "C2": asdict(c2)},
                C3_note="Same OOS dates; entirely post1980, no independent era check.",
                dsr=dsr_result,
            )
            if positive_gate:
                outcome.update(
                    G1=dsr_result["dsr"] > 0.95,
                    G2=c2.ci_low > 0.0,
                    positive_gate_pass=dsr_result["dsr"] > 0.95 and c2.ci_low > 0.0,
                )
            # The baseline must share the panel's exact calendar.  Reindexing
            # RF onto a live-store calendar inserts gaps and violates the
            # non-finite guard; no RF values are filled or fabricated here.
            baseline_px = data.build_matrix(["SPY", "IEF"], frozen_research_store()).reindex(index)
            for cost in COSTS:
                for label, weights in [("SPY", {"SPY": 1.0}), ("60/40", {"SPY": 0.6, "IEF": 0.4})]:
                    base = backtest.fixed_mix(
                        baseline_px, weights, cost_bps=cost, risk_free=rf
                    )
                    br = base.returns.reindex(oos)
                    if br.isna().any():
                        raise ValueError("baseline does not cover OOS calendar")
                    summaries.append(
                        dict(
                            strategy=label,
                            cost_bps=cost,
                            **metrics.summarize(
                                br, base.turnover.reindex(oos), rf_daily=rf.loc[oos]
                            ),
                        )
                    )
            pd.DataFrame(summaries).to_csv(path / "metrics.csv", index=False)
        except ValueError as error:
            outcome.update(
                status="refused",
                failure={"phase": "OOS", "reason": str(error)},
                C1=None,
                C2=None,
                C3=None,
            )
    if outcome["status"] == "completed":
        if defer_success_ledger:
            outcome["_ledger_study"] = study
            outcome["_ledger_records"] = staged
        else:
            outcome.update(commit_completed_ledger(study, staged))
    else:
        outcome["aborted_rows"] = len(staged)
        _write_ledger_batch(study, staged, status="aborted")
    serializable = {key: value for key, value in outcome.items() if not key.startswith("_ledger_")}
    (path / "summary.json").write_text(json.dumps(serializable, indent=2, default=str))
    return outcome


def main() -> None:
    prereg = ROOT / "journal/2026-09-07-xsmom-v16-panel-preregistration.md"
    if not prereg.exists():
        raise ValueError("Preregistration required")
    inputs_path = OUT / "inputs.json"
    verify_pinned_input(inputs_path)
    metadata = json.loads(inputs_path.read_text())
    verify_pinned_input(PANEL)
    if etf_snapshot() != metadata["snapshot"] or file_hash(PANEL) != metadata["panel_sha256"]:
        raise ValueError("Pinned inputs changed")
    panel = pd.read_parquet(PANEL)
    outcomes = []
    for arm in ["A", "B"]:
        print("Starting arm " + arm, flush=True)
        result = execute(panel, arm, metadata["snapshot"])
        outcomes.append(result)
        print(arm + ": " + result["status"], flush=True)
    verify_pinned_input(PANEL)
    if file_hash(PANEL) != metadata["panel_sha256"]:
        raise ValueError("Panel changed")
    report = dict(
        snapshot=metadata["snapshot"],
        panel_as_of=metadata["panel_as_of"],
        panel_sha256=metadata["panel_sha256"],
        reporting_block=REPORTING_BLOCK,
        arms=outcomes,
        gate_agreement={
            c: outcomes[0][c] == outcomes[1][c] if all(o[c] is not None for o in outcomes) else None
            for c in ["C1", "C2", "C3"]
        },
        no_price_changes=True,
        no_synthetic_bars=True,
        tuned_after_results=False,
    )
    (OUT / "summary.json").write_text(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
