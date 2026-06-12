# TradeBot Documentation

A Taiwan-stock (TWSE) focused algorithmic trading platform supporting live trading, historical backtesting, and time-mocked simulation. Geared toward the TWSE market: providers in `market/provider/` are TWSE/FinMind/Yahoo Finance, brokers include a real Shioaji adapter plus a `MockBroker` for development, and market hours are 9:00–13:30 with end-of-day data finalization at 18:00.

There is no formal packaging (`pyproject.toml`, `setup.py`, etc.) — modules are run directly from the repo root and rely on `requirements.txt` for dependencies.

## Table of Contents

1. [Architecture](./architecture.md) — High-level system design, threads, processes, mode dispatch.
2. [Configuration & Paths](./configuration.md) — `AppConfig` schema, config files, mode-specific path rewrites.
3. [Core Orchestrator](./core.md) — `Core` class, 5 background services, `TradingStatus` shared state.
4. [Market Data](./market-data.md) — Providers (TWSE/FinMind/Yahoo), caching, `MarketTime`, `DataProvider` base.
5. [Broker Layer](./broker.md) — `BrokerManager` singleton, order events, `MockBroker`, `ShioajiBroker`.
6. [Strategies](./strategies.md) — `StrategyManager` registry, `MovingProfitStrategy` base, all candidate/experimental strategies.
7. [Trading Engine](./trading.md) — `Evaluate`, `Trading`, `Recorder`, trade CLI.
8. [Backtest](./backtest.md) — `Backtest` engine, `BTCLI`, `PartialTradeAnalyzer`.
9. [Simulate](./simulate.md) — Time-mocked simulator in a separate process, `SimulateCLI`.
10. [StockWatch Web UI](./stockwatch.md) — Flask server for open trades & transactions.
11. [Testing Framework](./testing.md) — Custom CLI-driven test runner and suites.
12. [Development Guide](./development.md) — Conventions, logging, known issues, extension points.

## Quick Reference

### Run the application

All modes are launched through the single entry point `investor.py`:

```bash
# Live trading with mock broker (default) — development mode, no real money
python investor.py

# Live trading with real Shioaji broker — requires interactive "yes" confirmation
python investor.py --broker shioaji

# Backtest
python investor.py -b
python investor.py --backtest

# Simulation (time-mocked multi-process simulator)
python investor.py -s
python investor.py --simulate

# Internal test suite
python investor.py -t
```

### Module Map (top-level packages)

| Package           | Purpose                                                                            |
|-------------------|------------------------------------------------------------------------------------|
| `core/`           | Orchestrator, config schema, sqlite helpers                                         |
| `market/`         | Data providers, market timing, product info                                         |
| `broker/`         | Broker abstraction, order event pipeline, transaction log                          |
| `strategy/`       | Backtrader strategies organized by maturity level                                  |
| `trading/`        | Evaluate / buy / sell lifecycle, trade recording, live trade CLI                    |
| `backtest/`       | Historical backtester with custom analyzers                                         |
| `simulate/`       | Time-mocked simulator (separate process)                                            |
| `stockwatch/`     | Flask web UI for open trades & transactions                                        |
| `testutility/`    | CLI-driven test runner and per-package test suites                                 |
| `utility/`        | Framework helpers: config, CLI, debug logging, parallel processing, DB, time utils |

### Threading / Process Model

- **Live (`-m trade`)**: single process, 5 daemon threads orchestrated by `Core`.
- **Simulate (`-m simulate`)**: a separate `multiprocessing.Process` so `freezegun` can mock time inside it.
- **Backtest / Test**: single-process, no long-lived threads.

See [architecture.md](./architecture.md) for details.

## Key Conventions

- The custom logger in `utility/debug.py` is used everywhere — prefer `dbg_info`/`dbg_warning`/`dbg_error` over `print` or `logging`.
- Config access goes through `AppConfigManager` (`cm.get`, `cm.set`, `cm.get_path`); mutate via dot-notation.
- All sleeps that block a service thread should use `sleep_with_flag` / `sleep_until_with_flag` so `stop_event` is honored.
- `BrokerManager.initialize(broker_type=...)` must be called before constructing `Trading`, `Simulate`, or any `BrokerManager()` instance.

## Known Issues

The README's `FIXME`/`TODO`/`Potential Risk` sections are the canonical list of known issues. See [development.md](./development.md#known-issues) for the full list.
