# PropGuard

[![CI](https://github.com/fesrr/propguard/actions/workflows/ci.yml/badge.svg)](https://github.com/fesrr/propguard/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

**PropGuard** is a zero-dependency Python library and CLI for proprietary trading firm risk compliance, backtest telemetry, and Monte Carlo ruin analysis.

It audits CSV trade logs (from MetaTrader 5, TradingView exports, or custom algorithmic trading bots) against strict daily and total drawdown rules, calculates key risk-adjusted metrics, and estimates challenge pass/ruin probabilities before deploying capital.

## Features

- **Prop-Firm Rule Compliance:** Enforces configurable daily drawdown limits (e.g., 3%), maximum static or trailing total drawdown limits (e.g., 10%), and profit targets.
- **Quantitative Telemetry:** Computes Net Profit, Return %, Win Rate, Profit Factor, Expectancy, Annualized Sharpe Ratio, and Max Consecutive Losses.
- **Monte Carlo Ruin Simulator:** Estimates pass rate, ruin probability, and unresolved probability across thousands of randomized trade sequences.
- **Zero External Dependencies:** Built purely on the Python 3.10+ standard library for maximum portability and auditability.
- **JSON & Terminal Output:** Designed for both human review and automated CI/bot pipelines.

## Installation

```bash
pip install git+https://github.com/fesrr/propguard.git
```

Or clone and run directly:

```bash
git clone https://github.com/fesrr/propguard.git
cd propguard
PYTHONPATH=src python3 -m propguard.cli analyze examples/sample_trades.csv
```

## CLI Quickstart

### Analyze a Trade Log

```bash
propguard analyze examples/sample_trades.csv --balance 100000 --daily-dd 0.03 --total-dd 0.10
```

Sample output:

```text
PropGuard Report [COMPLIANT]
  Balance       : $100,000.00 -> $108,120.00 (+8.12%)
  Trades        : 8 | Win Rate: 75.00% | PF: 9.29
  Expectancy    : $1,015.00 | Sharpe: 16.2
  Max Daily DD  : 0.47% ($480.00)
  Max Total DD  : 0.49% ($500.00)
  Target Reached: False
```

### Run Monte Carlo Ruin Simulation

```bash
propguard simulate --win-rate 0.55 --rr 2.0 --risk 0.01 --runs 2000
```

## Python API

```python
from propguard import PropRules, RiskEngine, load_trades_csv

rules = PropRules(
    initial_balance=100_000.0,
    max_daily_drawdown_pct=0.03,
    max_total_drawdown_pct=0.10,
    profit_target_pct=0.10,
)
trades = load_trades_csv("examples/sample_trades.csv")
report = RiskEngine(rules).analyze(trades)

print("Compliant:", report.is_compliant)
print("Sharpe Ratio:", report.sharpe_ratio)
```

## Running Tests

```bash
python3 -m unittest discover -s tests -v
```

## Security & Contributing

- See [SECURITY.md](SECURITY.md) for vulnerability reporting guidelines.
- See [CONTRIBUTING.md](CONTRIBUTING.md) for development and pull request instructions.

## License

Released under the [MIT License](LICENSE).
