from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class PropRules:
    """Risk boundaries modeled after standard proprietary trading firm rules."""

    initial_balance: float = 100_000.0
    max_daily_drawdown_pct: float = 0.03
    max_total_drawdown_pct: float = 0.10
    profit_target_pct: float = 0.10
    trailing_drawdown: bool = False

    def __post_init__(self) -> None:
        if self.initial_balance <= 0:
            raise ValueError("initial_balance must be positive.")
        if not (0 < self.max_daily_drawdown_pct < 1):
            raise ValueError("max_daily_drawdown_pct must be between 0 and 1.")
        if not (0 < self.max_total_drawdown_pct < 1):
            raise ValueError("max_total_drawdown_pct must be between 0 and 1.")


@dataclass(frozen=True)
class TradeRecord:
    """Single closed trade record."""

    timestamp: str
    symbol: str
    side: str
    pnl: float
    risk_amount: Optional[float] = None

    @property
    def trade_date(self) -> str:
        """Extract YYYY-MM-DD date from ISO-like timestamp."""
        try:
            return datetime.fromisoformat(self.timestamp.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except ValueError:
            return self.timestamp[:10]


@dataclass
class RiskReport:
    """Aggregated performance and prop-firm compliance report."""

    initial_balance: float
    final_balance: float
    net_profit: float
    return_pct: float
    total_trades: int
    win_rate_pct: float
    profit_factor: float
    expectancy: float
    max_drawdown_abs: float
    max_drawdown_pct: float
    worst_daily_drawdown_abs: float
    worst_daily_drawdown_pct: float
    max_consecutive_losses: int
    sharpe_ratio: float
    passed_daily_limit: bool
    passed_total_limit: bool
    reached_profit_target: bool
    breach_reasons: List[str] = field(default_factory=list)

    @property
    def is_compliant(self) -> bool:
        return self.passed_daily_limit and self.passed_total_limit


class RiskEngine:
    """Evaluates trade logs against prop-firm risk limits and computes telemetry."""

    def __init__(self, rules: Optional[PropRules] = None) -> None:
        self.rules = rules or PropRules()

    def analyze(self, trades: Iterable[TradeRecord]) -> RiskReport:
        trade_list = list(trades)
        if not trade_list:
            raise ValueError("At least one trade record is required for analysis.")

        balance = self.rules.initial_balance
        peak_balance = balance
        max_dd_abs = 0.0
        max_dd_pct = 0.0

        daily_start_balance = balance
        current_day: Optional[str] = None
        daily_min_balance = balance
        worst_daily_dd_abs = 0.0
        worst_daily_dd_pct = 0.0

        wins = 0
        gross_profit = 0.0
        gross_loss = 0.0
        consecutive_losses = 0
        max_consecutive_losses = 0
        returns: List[float] = []

        for trade in trade_list:
            day = trade.trade_date
            if current_day != day:
                current_day = day
                daily_start_balance = balance
                daily_min_balance = balance

            prev_balance = balance
            balance += trade.pnl
            if prev_balance > 0:
                returns.append(trade.pnl / prev_balance)

            if balance > peak_balance:
                peak_balance = balance

            ref_peak = peak_balance if self.rules.trailing_drawdown else max(self.rules.initial_balance, peak_balance)
            dd_abs = max(0.0, ref_peak - balance)
            dd_pct = dd_abs / ref_peak if ref_peak > 0 else 0.0
            max_dd_abs = max(max_dd_abs, dd_abs)
            max_dd_pct = max(max_dd_pct, dd_pct)

            if balance < daily_min_balance:
                daily_min_balance = balance
            daily_dd_abs = max(0.0, daily_start_balance - daily_min_balance)
            daily_dd_pct = daily_dd_abs / daily_start_balance if daily_start_balance > 0 else 0.0
            worst_daily_dd_abs = max(worst_daily_dd_abs, daily_dd_abs)
            worst_daily_dd_pct = max(worst_daily_dd_pct, daily_dd_pct)

            if trade.pnl > 0:
                wins += 1
                gross_profit += trade.pnl
                consecutive_losses = 0
            elif trade.pnl < 0:
                gross_loss += abs(trade.pnl)
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

        total_trades = len(trade_list)
        net_profit = balance - self.rules.initial_balance
        return_pct = (net_profit / self.rules.initial_balance) * 100.0
        win_rate_pct = (wins / total_trades) * 100.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (math.inf if gross_profit > 0 else 0.0)
        expectancy = net_profit / total_trades
        sharpe = _compute_sharpe(returns)

        passed_daily = worst_daily_dd_pct <= self.rules.max_daily_drawdown_pct
        passed_total = max_dd_pct <= self.rules.max_total_drawdown_pct
        reached_target = (net_profit / self.rules.initial_balance) >= self.rules.profit_target_pct

        breaches: List[str] = []
        if not passed_daily:
            breaches.append(
                f"Daily drawdown {worst_daily_dd_pct * 100:.2f}% exceeded limit {self.rules.max_daily_drawdown_pct * 100:.2f}%"
            )
        if not passed_total:
            breaches.append(
                f"Total drawdown {max_dd_pct * 100:.2f}% exceeded limit {self.rules.max_total_drawdown_pct * 100:.2f}%"
            )

        return RiskReport(
            initial_balance=self.rules.initial_balance,
            final_balance=round(balance, 2),
            net_profit=round(net_profit, 2),
            return_pct=round(return_pct, 2),
            total_trades=total_trades,
            win_rate_pct=round(win_rate_pct, 2),
            profit_factor=round(profit_factor, 2) if math.isfinite(profit_factor) else math.inf,
            expectancy=round(expectancy, 2),
            max_drawdown_abs=round(max_dd_abs, 2),
            max_drawdown_pct=round(max_dd_pct * 100.0, 2),
            worst_daily_drawdown_abs=round(worst_daily_dd_abs, 2),
            worst_daily_drawdown_pct=round(worst_daily_dd_pct * 100.0, 2),
            max_consecutive_losses=max_consecutive_losses,
            sharpe_ratio=round(sharpe, 2),
            passed_daily_limit=passed_daily,
            passed_total_limit=passed_total,
            reached_profit_target=reached_target,
            breach_reasons=breaches,
        )


def _compute_sharpe(returns: List[float]) -> float:
    if len(returns) < 2:
        return 0.0
    mean_r = sum(returns) / len(returns)
    variance = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
    std_r = math.sqrt(variance)
    if std_r == 0:
        return 0.0
    return (mean_r / std_r) * math.sqrt(252)


def load_trades_csv(path: str | Path) -> List[TradeRecord]:
    """Load trade records from a CSV file with columns: timestamp,symbol,side,pnl[,risk_amount]."""
    trades: List[TradeRecord] = []
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            risk_val = row.get("risk_amount")
            trades.append(
                TradeRecord(
                    timestamp=row["timestamp"].strip(),
                    symbol=row["symbol"].strip(),
                    side=row["side"].strip().upper(),
                    pnl=float(row["pnl"]),
                    risk_amount=float(risk_val) if risk_val not in (None, "") else None,
                )
            )
    return trades


def monte_carlo_ruin(
    win_rate: float,
    reward_to_risk: float,
    risk_per_trade_pct: float = 0.01,
    max_drawdown_pct: float = 0.10,
    profit_target_pct: float = 0.10,
    trades_per_run: int = 100,
    simulations: int = 2000,
    seed: Optional[int] = 42,
) -> dict[str, float]:
    """Estimate pass rate and ruin probability under prop-firm drawdown constraints."""
    if not (0 < win_rate < 1):
        raise ValueError("win_rate must be between 0 and 1.")
    if reward_to_risk <= 0:
        raise ValueError("reward_to_risk must be positive.")

    rng = random.Random(seed)
    passed = 0
    ruined = 0

    for _ in range(simulations):
        equity = 1.0
        for _ in range(trades_per_run):
            if rng.random() < win_rate:
                equity *= 1.0 + risk_per_trade_pct * reward_to_risk
            else:
                equity *= 1.0 - risk_per_trade_pct

            if equity <= 1.0 - max_drawdown_pct:
                ruined += 1
                break
            if equity >= 1.0 + profit_target_pct:
                passed += 1
                break

    return {
        "simulations": float(simulations),
        "pass_rate_pct": round((passed / simulations) * 100.0, 2),
        "ruin_rate_pct": round((ruined / simulations) * 100.0, 2),
        "unresolved_pct": round(((simulations - passed - ruined) / simulations) * 100.0, 2),
    }
