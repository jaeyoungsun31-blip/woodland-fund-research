"""Deflated Sharpe ratio — Bailey & Lopez de Prado (DESIGN.md §7).

The point: a Sharpe ratio is a maximum taken over however many configurations
you tried, and the maximum of N draws from a zero-skill distribution is
comfortably positive. The deflated Sharpe ratio asks the only question that
matters — given that I ran N trials whose Sharpes were this spread out, over
this many observations, with returns this skewed and fat-tailed, what is the
probability the true Sharpe of the survivor is above zero?

Two corrections, both of which cut in the honest direction:

  * Selection.  The benchmark is not 0 but SR0, the Sharpe you would expect
    the BEST of N trials to show under the null. SR0 grows with N and with
    the spread of trial Sharpes.
  * Non-normality.  Negative skew and fat tails make a Sharpe less
    trustworthy than the normal-theory standard error suggests, so they widen
    the denominator.

Uses `statistics.NormalDist` from the stdlib — no scipy dependency for two
functions.

Reference: Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio:
Correcting for Selection Bias, Backtest Overfitting, and Non-Normality."
"""

from __future__ import annotations

import math
from statistics import NormalDist
from typing import cast

import numpy as np
import pandas as pd

EULER_MASCHERONI = 0.5772156649015329
_N = NormalDist()
TRADING_DAYS = 252


def probabilistic_sharpe(
    sr: float, benchmark_sr: float, n_obs: int, skew: float, kurtosis: float
) -> float:
    """P(true Sharpe > benchmark). All Sharpes in PER-PERIOD units.

    `kurtosis` is non-excess (a normal distribution scores 3.0).
    """
    if n_obs < 2:
        return float("nan")
    var = 1.0 - skew * sr + (kurtosis - 1.0) / 4.0 * sr**2
    if var <= 0 or not math.isfinite(var):
        return float("nan")
    z = (sr - benchmark_sr) * math.sqrt(n_obs - 1) / math.sqrt(var)
    return _N.cdf(z)


def expected_max_sharpe(var_trial_sr: float, n_trials: int) -> float:
    """SR0: the Sharpe the BEST of `n_trials` shows under the null of no skill.

    Per-period units. With a single trial there is no selection to correct
    for, so SR0 is 0.
    """
    if n_trials < 2 or var_trial_sr <= 0 or not math.isfinite(var_trial_sr):
        return 0.0
    g = EULER_MASCHERONI
    z1 = _N.inv_cdf(1.0 - 1.0 / n_trials)
    z2 = _N.inv_cdf(1.0 - 1.0 / (n_trials * math.e))
    return math.sqrt(var_trial_sr) * ((1.0 - g) * z1 + g * z2)


def deflated_sharpe(
    returns: pd.Series,
    n_trials: int,
    *,
    trial_sharpes: pd.Series | np.ndarray | None = None,
    var_trial_sr_annual: float | None = None,
    periods_per_year: int = TRADING_DAYS,
) -> dict:
    """Deflate an observed return series' Sharpe for selection and non-normality.

    returns              : the SURVIVING strategy's per-period returns
    n_trials             : how many configurations were evaluated to find it
                           (take this from the trials ledger, never from memory)
    trial_sharpes        : ANNUALIZED Sharpes of those trials; their variance is
                           the spread term. Supply this or `var_trial_sr_annual`.
    var_trial_sr_annual  : variance of the annualized trial Sharpes, if the
                           individual values are not to hand.

    Returns a dict; `dsr` is the probability the true Sharpe beats SR0. Read a
    dsr below ~0.95 as "this is not distinguishable from the best of N
    coin-flips".
    """
    r = pd.Series(returns).dropna()
    n_obs = len(r)
    sqrt_ppy = math.sqrt(periods_per_year)

    if trial_sharpes is not None:
        ts = pd.Series(trial_sharpes).dropna()
        var_annual = float(ts.var(ddof=1)) if len(ts) > 1 else 0.0
        trial_min = float(ts.min()) if len(ts) else float("nan")
        trial_max = float(ts.max()) if len(ts) else float("nan")
    elif var_trial_sr_annual is not None:
        var_annual = float(var_trial_sr_annual)
        trial_min = trial_max = float("nan")
    else:
        raise ValueError("supply trial_sharpes or var_trial_sr_annual")

    sd = float(r.std(ddof=1)) if n_obs > 1 else 0.0
    if n_obs < 2 or sd <= 0:
        return {
            "sharpe_annual": float("nan"), "sr0_annual": float("nan"),
            "dsr": float("nan"), "n_obs": n_obs, "n_trials": int(n_trials),
            "note": "insufficient or degenerate return series",
        }

    sr_period = float(r.mean()) / sd
    var_period = var_annual / periods_per_year      # Var scales as 1/periods
    sr0_period = expected_max_sharpe(var_period, int(n_trials))

    skew = float(cast(float, r.skew()))
    kurt = float(cast(float, r.kurt())) + 3.0  # pandas reports EXCESS kurtosis

    dsr = probabilistic_sharpe(sr_period, sr0_period, n_obs, skew, kurt)
    psr0 = probabilistic_sharpe(sr_period, 0.0, n_obs, skew, kurt)

    return {
        "sharpe_annual": sr_period * sqrt_ppy,
        "sr0_annual": sr0_period * sqrt_ppy,
        "dsr": dsr,
        "psr_vs_zero": psr0,
        "n_obs": n_obs,
        "n_trials": int(n_trials),
        "trial_sharpe_sd_annual": math.sqrt(var_annual),
        "trial_sharpe_min_annual": trial_min,
        "trial_sharpe_max_annual": trial_max,
        "trial_sharpe_spread_annual": trial_max - trial_min,
        "skew": skew,
        "excess_kurtosis": kurt - 3.0,
        "years": n_obs / periods_per_year,
    }


def report(result: dict) -> str:
    """One-paragraph rendering, phrased so the number cannot be over-read."""
    if not math.isfinite(result.get("dsr", float("nan"))):
        return f"deflated Sharpe: not computable ({result.get('note', 'unknown')})"
    return (
        f"Sharpe {result['sharpe_annual']:.2f} annualized over {result['years']:.1f}y "
        f"({result['n_obs']} obs).\n"
        f"Selection hurdle after {result['n_trials']} trials: SR0 = "
        f"{result['sr0_annual']:.2f} (trial Sharpe sd {result['trial_sharpe_sd_annual']:.2f}).\n"
        f"Effective breadth: {result['n_trials']} distinct configs; train-window Sharpe "
        f"range {result['trial_sharpe_min_annual']:.3f}.."
        f"{result['trial_sharpe_max_annual']:.3f}, spread "
        f"{result['trial_sharpe_spread_annual']:.3f}. Near-collinear trials make this "
        f"a weak selection hurdle.\n"
        f"Deflated Sharpe (P[true SR > SR0]) = {result['dsr']:.3f}; "
        f"P[true SR > 0] ignoring selection = {result['psr_vs_zero']:.3f}.\n"
        f"skew {result['skew']:.2f}, excess kurtosis {result['excess_kurtosis']:.2f}.\n"
        f"A DSR below 0.95 does not clear the bar: it means the result is not "
        f"distinguishable from the best of {result['n_trials']} lottery tickets."
    )
