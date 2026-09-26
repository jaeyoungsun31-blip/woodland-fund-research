"""French prior-return decile parsing and model-implied migration turnover."""

from __future__ import annotations

import math
import zipfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

DECILE_COLUMNS = ["Lo PRIOR", *[f"PRIOR {number}" for number in range(2, 10)], "Hi PRIOR"]
RANK_CORRELATION = 229.0 / 230.0
QUADRATURE_NODES = 256


@dataclass(frozen=True)
class HoldingTurnover:
    """Annualized turnover components for a modeled stale cohort."""

    internal: float
    initial_purchase: float

    @property
    def total(self) -> float:
        return self.internal + self.initial_purchase


def parse_daily_deciles(path: Path | str) -> pd.DataFrame:
    """Parse only the value-weighted daily return section of the French ZIP."""
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != 1:
            raise ValueError("expected exactly one file in momentum archive")
        text = archive.read(names[0]).decode("utf-8")
    lines = text.splitlines()
    section = next(
        (i for i, line in enumerate(lines) if "Average Value Weighted Returns -- Daily" in line),
        None,
    )
    if section is None or section + 1 >= len(lines):
        raise ValueError("value-weighted daily section not found")
    header = [value.strip() for value in lines[section + 1].split(",")][1:]
    if header != DECILE_COLUMNS:
        raise ValueError(f"unexpected decile columns: {header}")
    rows: list[list[object]] = []
    for line in lines[section + 2:]:
        fields = [value.strip() for value in line.split(",")]
        if not fields or len(fields[0]) != 8 or not fields[0].isdigit():
            if rows:
                break
            continue
        if len(fields) != 11:
            raise ValueError(f"malformed daily row {fields[0]}")
        rows.append([pd.Timestamp(fields[0]), *[float(value) for value in fields[1:]]])
    if not rows:
        raise ValueError("no daily decile returns parsed")
    frame = pd.DataFrame(rows, columns=["Date", *header]).set_index("Date")
    return frame.replace([-99.99, -999.0], np.nan).div(100.0).sort_index()


def normal_decile_boundaries() -> list[float]:
    normal = NormalDist()
    return [float("-inf"), *[normal.inv_cdf(i / 10.0) for i in range(1, 10)],
            float("inf")]


def formation_dates(index: pd.DatetimeIndex, frequency: str) -> pd.DatetimeIndex:
    """Last observed trading date in each requested calendar period."""
    if not index.is_monotonic_increasing or index.has_duplicates:
        raise ValueError("index must be sorted and unique")
    if frequency == "monthly":
        groups: pd.Index = index.to_period("M")
    elif frequency == "quarterly":
        groups = index.to_period("Q")
    elif frequency == "semiannual":
        groups = index.year * 2 + (index.month > 6).astype(int)
    elif frequency == "annual":
        groups = index.year
    else:
        raise ValueError(f"unsupported formation frequency: {frequency}")
    dates = pd.Series(index=index, data=index).groupby(groups).max()
    return pd.DatetimeIndex(dates.to_numpy())


def _normal_cdf(values: np.ndarray) -> np.ndarray:
    return np.asarray(
        [0.5 * (1.0 + math.erf(float(value) / math.sqrt(2.0))) for value in values]
    )


@lru_cache(maxsize=2_048)
def _stale_cohort_weights_cached(
    steps: int,
    lower_probability: float,
    upper_probability: float,
    rho: float,
    quadrature_nodes: int,
) -> tuple[float, ...]:
    if steps < 0:
        raise ValueError("steps must be non-negative")
    if not 0.0 <= lower_probability < upper_probability <= 1.0:
        raise ValueError("probability interval must satisfy 0 <= lower < upper <= 1")
    if not -1.0 < rho < 1.0:
        raise ValueError("rho must be in (-1, 1)")
    if quadrature_nodes < 8:
        raise ValueError("quadrature_nodes must be at least 8")

    mass = upper_probability - lower_probability
    if steps == 0:
        weights = [
            max(0.0, min(upper_probability, j / 10.0) - max(lower_probability, (j - 1) / 10.0))
            / mass
            for j in range(1, 11)
        ]
        return tuple(weights)

    normal = NormalDist()
    source_lower = (
        -8.0 if lower_probability == 0.0 else normal.inv_cdf(lower_probability)
    )
    source_upper = (
        8.0 if upper_probability == 1.0 else normal.inv_cdf(upper_probability)
    )
    nodes, quadrature_weights = np.polynomial.legendre.leggauss(quadrature_nodes)
    half_width = (source_upper - source_lower) / 2.0
    midpoint = (source_upper + source_lower) / 2.0
    x = midpoint + half_width * nodes
    integration_weights = (
        half_width
        * quadrature_weights
        * np.exp(-0.5 * x**2)
        / math.sqrt(2.0 * math.pi)
    )
    correlation = rho**steps
    conditional_sd = math.sqrt(1.0 - correlation**2)
    boundaries = normal_decile_boundaries()
    joint_probabilities: list[float] = []
    for lower, upper in zip(boundaries[:-1], boundaries[1:], strict=True):
        upper_cdf = (
            np.ones_like(x)
            if math.isinf(upper)
            else _normal_cdf((upper - correlation * x) / conditional_sd)
        )
        lower_cdf = (
            np.zeros_like(x)
            if math.isinf(lower)
            else _normal_cdf((lower - correlation * x) / conditional_sd)
        )
        joint_probabilities.append(
            float(np.sum(integration_weights * (upper_cdf - lower_cdf)))
        )
    weights = np.clip(np.asarray(joint_probabilities, dtype=float), 0.0, None)
    total = float(weights.sum())
    if total <= 0.0:
        raise ValueError("quadrature produced zero cohort mass")
    return tuple((weights / total).tolist())


def stale_cohort_weights(
    steps: int,
    *,
    lower_probability: float = 0.7,
    upper_probability: float = 1.0,
    rho: float = RANK_CORRELATION,
    quadrature_nodes: int = QUADRATURE_NODES,
) -> np.ndarray:
    """Current-decile mass of a cohort selected ``steps`` transitions ago."""
    return np.asarray(
        _stale_cohort_weights_cached(
            steps, lower_probability, upper_probability, rho, quadrature_nodes
        )
    )


def stale_cohort_returns(
    decile_returns: pd.DataFrame,
    dates: pd.DatetimeIndex,
    *,
    rho: float = RANK_CORRELATION,
    quadrature_nodes: int = QUADRATURE_NODES,
) -> pd.Series:
    """Model a top-30% cohort, with close-t formation first affecting t+1."""
    if list(decile_returns.columns) != DECILE_COLUMNS:
        raise ValueError("decile returns must have the standard ordered columns")
    if not decile_returns.index.is_monotonic_increasing or decile_returns.index.has_duplicates:
        raise ValueError("decile return index must be sorted and unique")
    if decile_returns.isna().any().any():
        raise ValueError("decile returns must be complete")
    unknown = dates.difference(pd.DatetimeIndex(decile_returns.index))
    if len(unknown):
        raise ValueError("formation dates must belong to the return index")

    formation_set = set(dates)
    values = decile_returns.to_numpy(dtype=float)
    modeled = np.zeros(len(values), dtype=float)
    active = False
    age = 0
    for position, date in enumerate(decile_returns.index):
        if active:
            modeled[position] = float(
                stale_cohort_weights(
                    age, rho=rho, quadrature_nodes=quadrature_nodes
                )
                @ values[position]
            )
            age += 1
        if date in formation_set and position < len(values) - 1:
            active = True
            age = 0
    return pd.Series(modeled, index=decile_returns.index, name="ret")


def holding_period_turnover(
    index: pd.DatetimeIndex,
    dates: pd.DatetimeIndex,
    *,
    rho: float = RANK_CORRELATION,
    quadrature_nodes: int = QUADRATURE_NODES,
) -> HoldingTurnover:
    """Annualized refresh turnover for the modeled top-30% cohort."""
    if len(index) < 2:
        raise ValueError("need at least two return bars")
    if not index.is_monotonic_increasing or index.has_duplicates:
        raise ValueError("index must be sorted and unique")
    usable = dates[dates < index[-1]]
    unknown = usable.difference(index)
    if len(unknown):
        raise ValueError("formation dates must belong to the return index")
    positions = index.get_indexer(usable)
    if not len(positions):
        return HoldingTurnover(internal=0.0, initial_purchase=0.0)
    internal_sum = 0.0
    for prior, current in zip(positions[:-1], positions[1:], strict=True):
        elapsed = int(current - prior)
        surviving = float(
            stale_cohort_weights(
                elapsed, rho=rho, quadrature_nodes=quadrature_nodes
            )[-3:].sum()
        )
        internal_sum += 2.0 * (1.0 - surviving)
    years = len(index) / 252.0
    return HoldingTurnover(
        internal=internal_sum / years,
        initial_purchase=1.0 / years,
    )


@lru_cache(maxsize=64)
def model_implied_turnover(
    lower_probability: float,
    upper_probability: float,
    *,
    rho: float = RANK_CORRELATION,
    trading_days: int = 252,
    grid_size: int = 20_001,
) -> float:
    """Annual sum-absolute turnover implied by Gaussian rank transitions."""
    if not 0.0 <= lower_probability < upper_probability <= 1.0:
        raise ValueError("probability interval must satisfy 0 <= lower < upper <= 1")
    if not -1.0 < rho < 1.0:
        raise ValueError("rho must be in (-1, 1)")
    normal = NormalDist()
    lower = -8.0 if lower_probability == 0.0 else normal.inv_cdf(lower_probability)
    upper = 8.0 if upper_probability == 1.0 else normal.inv_cdf(upper_probability)
    x = np.linspace(lower, upper, grid_size)
    conditional_sd = math.sqrt(1.0 - rho**2)

    inside_upper = (
        np.ones_like(x)
        if upper_probability == 1.0
        else _normal_cdf((upper - rho * x) / conditional_sd)
    )
    inside_lower = (
        np.zeros_like(x)
        if lower_probability == 0.0
        else _normal_cdf((lower - rho * x) / conditional_sd)
    )
    density = np.exp(-0.5 * x**2) / math.sqrt(2.0 * math.pi)
    stay_joint = float(np.trapezoid(density * (inside_upper - inside_lower), x))
    mass = upper_probability - lower_probability
    exit_rate = max(0.0, min(1.0, (mass - stay_joint) / mass))
    return 2.0 * trading_days * exit_rate


def net_of_internal_cost(
    returns: pd.Series, annual_turnover: float, cost_bps: float
) -> pd.Series:
    if annual_turnover < 0.0 or cost_bps < 0.0:
        raise ValueError("turnover and cost must be non-negative")
    return (returns - annual_turnover * cost_bps / 10_000.0 / 252.0).rename("ret")
