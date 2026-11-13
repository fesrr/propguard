"""PropGuard: Prop-firm risk compliance and backtest telemetry engine."""

from .engine import (
    PropRules,
    RiskEngine,
    RiskReport,
    TradeRecord,
    load_trades_csv,
    monte_carlo_ruin,
)

__all__ = [
    "PropRules",
    "RiskEngine",
    "RiskReport",
    "TradeRecord",
    "load_trades_csv",
    "monte_carlo_ruin",
]

__version__ = "1.0.0"
