import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from propguard import PropRules, RiskEngine, TradeRecord, load_trades_csv, monte_carlo_ruin


class TestPropGuard(unittest.TestCase):
    def test_compliant_session(self) -> None:
        rules = PropRules(initial_balance=100_000, max_daily_drawdown_pct=0.03, max_total_drawdown_pct=0.10, profit_target_pct=0.05)
        trades = [
            TradeRecord("2026-11-01T09:00:00Z", "XAUUSD", "BUY", 2500.0),
            TradeRecord("2026-11-01T12:00:00Z", "XAUUSD", "SELL", -1000.0),
            TradeRecord("2026-11-02T10:00:00Z", "EURUSD", "BUY", 4000.0),
        ]
        report = RiskEngine(rules).analyze(trades)
        self.assertTrue(report.is_compliant)
        self.assertTrue(report.reached_profit_target)
        self.assertEqual(report.final_balance, 105_500.0)
        self.assertEqual(report.max_consecutive_losses, 1)

    def test_daily_drawdown_breach(self) -> None:
        rules = PropRules(initial_balance=100_000, max_daily_drawdown_pct=0.03, max_total_drawdown_pct=0.10)
        trades = [
            TradeRecord("2026-11-01T09:00:00Z", "XAUUSD", "BUY", -3500.0),
            TradeRecord("2026-11-01T14:00:00Z", "XAUUSD", "BUY", 1000.0),
        ]
        report = RiskEngine(rules).analyze(trades)
        self.assertFalse(report.passed_daily_limit)
        self.assertTrue(report.passed_total_limit)
        self.assertFalse(report.is_compliant)
        self.assertEqual(len(report.breach_reasons), 1)

    def test_monte_carlo_simulation(self) -> None:
        res = monte_carlo_ruin(win_rate=0.55, reward_to_risk=2.0, risk_per_trade_pct=0.01, simulations=500, seed=7)
        self.assertGreater(res["pass_rate_pct"], res["ruin_rate_pct"])
        self.assertAlmostEqual(
            res["pass_rate_pct"] + res["ruin_rate_pct"] + res["unresolved_pct"],
            100.0,
            places=1,
        )

    def test_csv_loader(self) -> None:
        sample = Path(__file__).resolve().parents[1] / "examples" / "sample_trades.csv"
        trades = load_trades_csv(sample)
        self.assertGreaterEqual(len(trades), 5)


if __name__ == "__main__":
    unittest.main()
