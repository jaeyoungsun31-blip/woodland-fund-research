"""Operational retrain-loop components.

Research code produces evidence.  This package consumes already-registered
evidence, applies the frozen promotion gate, and either emits a bounded target
or refuses.  Importing it never reads or writes live state.
"""

from woodland.live.bands import DEFAULT_BAND, apply_no_trade_band
from woodland.live.gate import GateVerdict, PortfolioEvidence, evaluate_gate
from woodland.live.incumbent import Incumbent, IncumbentStore
from woodland.live.refusal import CycleHealth, RefusalVerdict, evaluate_refusal

__all__ = [
    "DEFAULT_BAND",
    "CycleHealth",
    "GateVerdict",
    "Incumbent",
    "IncumbentStore",
    "PortfolioEvidence",
    "RefusalVerdict",
    "apply_no_trade_band",
    "evaluate_gate",
    "evaluate_refusal",
]
