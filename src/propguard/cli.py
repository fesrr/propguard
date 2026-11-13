from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import List, Optional

from .engine import PropRules, RiskEngine, load_trades_csv, monte_carlo_ruin


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="propguard",
        description="Prop-firm risk compliance & backtest telemetry CLI.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    analyze_p = sub.add_parser("analyze", help="Analyze a CSV trade log against prop-firm limits.")
    analyze_p.add_argument("csv_path", help="Path to CSV file (timestamp,symbol,side,pnl)")
    analyze_p.add_argument("--balance", type=float, default=100_000.0, help="Initial account balance")
    analyze_p.add_argument("--daily-dd", type=float, default=0.03, help="Max daily drawdown fraction (e.g. 0.03)")
    analyze_p.add_argument("--total-dd", type=float, default=0.10, help="Max total drawdown fraction (e.g. 0.10)")
    analyze_p.add_argument("--target", type=float, default=0.10, help="Profit target fraction (e.g. 0.10)")
    analyze_p.add_argument("--trailing", action="store_true", help="Use trailing peak drawdown")
    analyze_p.add_argument("--json", action="store_true", help="Output report as JSON")

    sim_p = sub.add_parser("simulate", help="Run Monte Carlo pass/ruin simulation.")
    sim_p.add_argument("--win-rate", type=float, required=True, help="Win rate between 0 and 1 (e.g. 0.55)")
    sim_p.add_argument("--rr", type=float, required=True, help="Reward-to-risk ratio (e.g. 2.0)")
    sim_p.add_argument("--risk", type=float, default=0.01, help="Risk per trade fraction (e.g. 0.01)")
    sim_p.add_argument("--total-dd", type=float, default=0.10, help="Max total drawdown fraction")
    sim_p.add_argument("--target", type=float, default=0.10, help="Profit target fraction")
    sim_p.add_argument("--trades", type=int, default=100, help="Max trades per simulation")
    sim_p.add_argument("--runs", type=int, default=2000, help="Number of Monte Carlo runs")
    sim_p.add_argument("--json", action="store_true", help="Output simulation as JSON")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        rules = PropRules(
            initial_balance=args.balance,
            max_daily_drawdown_pct=args.daily_dd,
            max_total_drawdown_pct=args.total_dd,
            profit_target_pct=args.target,
            trailing_drawdown=args.trailing,
        )
        trades = load_trades_csv(args.csv_path)
        report = RiskEngine(rules).analyze(trades)
        if args.json:
            print(json.dumps(asdict(report), indent=2))
        else:
            status = "COMPLIANT" if report.is_compliant else "BREACHED"
            print(f"PropGuard Report [{status}]")
            print(f"  Balance       : ${report.initial_balance:,.2f} -> ${report.final_balance:,.2f} ({report.return_pct:+.2f}%)")
            print(f"  Trades        : {report.total_trades} | Win Rate: {report.win_rate_pct:.2f}% | PF: {report.profit_factor}")
            print(f"  Expectancy    : ${report.expectancy:,.2f} | Sharpe: {report.sharpe_ratio}")
            print(f"  Max Daily DD  : {report.worst_daily_drawdown_pct:.2f}% (${report.worst_daily_drawdown_abs:,.2f})")
            print(f"  Max Total DD  : {report.max_drawdown_pct:.2f}% (${report.max_drawdown_abs:,.2f})")
            print(f"  Target Reached: {report.reached_profit_target}")
            if report.breach_reasons:
                print("  Breaches:")
                for reason in report.breach_reasons:
                    print(f"    - {reason}")
        return 0 if report.is_compliant else 2

    if args.command == "simulate":
        result = monte_carlo_ruin(
            win_rate=args.win_rate,
            reward_to_risk=args.rr,
            risk_per_trade_pct=args.risk,
            max_drawdown_pct=args.total_dd,
            profit_target_pct=args.target,
            trades_per_run=args.trades,
            simulations=args.runs,
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("PropGuard Monte Carlo Simulation")
            print(f"  Simulations   : {int(result['simulations'])}")
            print(f"  Pass Rate     : {result['pass_rate_pct']:.2f}%")
            print(f"  Ruin Rate     : {result['ruin_rate_pct']:.2f}%")
            print(f"  Unresolved    : {result['unresolved_pct']:.2f}%")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
