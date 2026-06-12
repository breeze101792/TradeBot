# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**TradeBot** is a Taiwan-stock (TWSE) focused algorithmic trading platform. The system supports live trading, historical backtesting, and time-mocked simulation. It is geared toward the TWSE market: providers in `market/provider/` are TWSE/FinMind/Yahoo Finance, brokers include a real Shioaji adapter plus a `MockBroker` for development, and market hours are 9:00–13:30 with end-of-day data finalization at 18:00.

There is no formal packaging (`pyproject.toml`, `setup.py`, etc.) — modules are run directly from the repo root and rely on `requirements.txt` for dependencies.

## Common Commands

There are no project-level linters or test runners configured (no `pytest.ini`, `tox.ini`, `Makefile`, etc.). Tests are run through an in-app CLI.

### Install
```bash
pip install -r requirements.txt
```
The `shioaji[speed]` line is commented-in by default; comment it out if you do not have access to the Sinopac Shioaji SDK. `python-dotenv` is also commented out — enable if you need `.env` support.

### Activate virtual env
```bash
# Two venv dirs are present in the repo; either works
source .venv/bin/activate
# or
source .pyvenv/bin/activate
```

### Run the application
All modes are launched through the single entry point `investor.py`. The mode is selected via flags and branches at startup into one of four sub-CLIs.

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

# Internal test suite (run inside the test CLI)
python investor.py -t
```

### CLI flags summary
- `-d` / `--develoment` — enable development mode (note: typo is intentional, matches the source)
- `-m` / `--trade-mode {backtest,test,trade,simulate}` — mode selector
- `-b` / `--backtest` — shortcut for `-m backtest`
- `-t` / `--test` — shortcut for `-m test`
- `-s` / `--simulate` — shortcut for `-m simulate`
- `--broker {mock,shioaji}` — broker adapter
- `-p` / `--product-list 2330 2454 ...` — product IDs
- `--time-frame {day,week}` — backtest data granularity

### In-CLI commands
Each sub-CLI accepts its own commands after the prompt. Common ones:
- **TDCLI** (live trade prompt) — `status`, `sanity`, `update`, `buy`, `sell`, `server start`
- **BTCLI** (backtest prompt) — `info`, `start`, `date`, `product`, plus registered backtest commands
- **SimulateCLI** (simulation prompt) — `info`, `start`, `stop`, `pause`, `continue`, `ignore_pause`, `test [single|multiple|t1|t50|all|<year>]`, `date`, `product`, `update [all|force]`, `buy`, `sell`, `positions`, `transactions`, `trade`, `report`
- **TestCLI** (test prompt) — `core`, `market`, `trading`, `broker`, `backtest`, `integration`, `all`

## High-Level Architecture

`investor.py` is the entry point. It builds an `AppConfigManager`, then dispatches to one of four sub-CLIs based on `--trade-mode`. The `trade` mode runs the long-lived `Core` orchestrator with live threads; the other modes each spawn a separate CLI class.

### Module map (top-level packages)
- **`core/`** — orchestrator, config, sqlite helpers
  - `core.py` — `Core` class. Spawns 5 long-lived threads: `datasource_service` (refreshes market data), `trading_service` (runs strategy evaluation after market close, executes buys at next open), `selling_service` (intra-day 10-min loop while market is open), `broker_service` (reconnect/position summary around market open/close), `heatbeat_service` (sanity checks). Cross-thread state lives in a `TradingStatus` namespace (next wake-up times, target buying list).
  - `config.py` — `AppConfig` (lots/cash limits, paths, debug flag) + `AppConfigManager` (dot-notation get/set/get_path).
  - `database.py` — sqlite wrapper used by `trading/traderecord.py` and `trading/tradedata.py`.
- **`market/`** — data providers and market timing
  - `market.py` — `Market` aggregates `FindMind`, `TWSE`, `Yahoo` providers. `switch_market()` rebinds `MarketTime` open/close/update times from the active provider.
  - `provider/twse.py` — uses `twstock` plus `filelock`-guarded cache writes; 1.6s `API_CALL_INTERVAL_SECONDS` to dodge rate-limits.
  - `dataprovider.py` — base class; `get_data_list`, `download_data`, `cache_data_name` are the abstract surface.
- **`broker/`** — broker abstraction
  - `brokermanager.py` — singleton-style wrapper. `initialize(broker_type=...)` must be called before any other method (the `Core.initialize` and `Simulate` both do this). Class-level `_lock` + `reconnect()` handle broker connectivity; `lock(timeout=10)` also calls `broker.check_quota()`.
  - `brokers/base/basebroker.py` — `BaseBroker` interface; `brokers/mock/` and `brokers/shioaji/` are the two implementations.
  - `order/` — `OrderService`, `OrderTracker`, `Event` enum (`OrderFilled`, `OrderFailed`, `OrderPending`, `OrderCanceled`).
  - `transaction.py` — CSV-backed transaction log.
- **`strategy/`** — backtrader strategies
  - `strategy.py` — `StrategyManager` registers strategies at three `Level`s: `OFFICIAL` (production), `BETA` (active but unproven), `TESTING` (only loaded when `test > 0`).
  - `candidate/` — MAC, RSI, Bollinger mean reversion, breakout momentum, multi-signal.
  - `basic/` — `BasicStrategy` parent + `MovingProfit`.
  - `experiment/` — VWAP, Bollinger rebound, volume experiments, test stubs.
- **`trading/`** — business logic
  - `trading.py` — `Trading`: `BUYING_IGNORE` / `SELLING_IGNORE` static flags, `BUYING_CANDIDATE` map; `trading_eval()`, `buying_exec()`, `selling_eval()`, `selling_exec()`, `order_callback()`. The class subscribes to broker events to feed `Recorder`.
  - `evaluate.py` — scoring layer that takes market data + strategies and produces a candidate list.
  - `traderecord.py` — `Trade` and `Recorder`; an open `Trade` accumulates buy/sell transactions keyed by `trade_id` (uuid).
  - `tradedata.py` — DB I/O for trade history.
  - `tradecli.py` — `TDCLI` is the live-trading prompt; commands are registered at runtime by `Core.initialize()`.
- **`backtest/`** — backtrader-driven historical backtester
  - `btcli.py` — `BTCLI` (backtest prompt); uses `BacktestInfo` to serialize runs to JSON.
  - `backtest.py` / `datafeed.py` / `backresult.py` / `commands.py` / `analyzer/` — engine, custom feed, results reporting, registered commands.
- **`simulate/`** — time-mocked simulator that runs in a subprocess
  - `simulate.py` — `Simulate(multiprocessing.Process)`. Uses `freezegun` to mock wall time, advances `_simulation_time`, accepts commands via `command_queue` (multiprocessing.Queue), exposes `pause`/`continue` via shared `Value`s and `Event`. State is persisted under `path.broker = "simulate/<timestamp>"`.
  - `simulatecli.py` — `SimulateCLI` (simulation prompt); `ParallelProcessor` is used for `exp` command parallelizing per-symbol analysis.
- **`testutility/`** — `unittest.mock`-based test cases invoked from the TestCLI prompt
  - `testcli.py` registers six test groups: `core`, `market`, `trading`, `broker`, `backtest`, `integration`. Each module exports a `*_TEST_CASES` list.
- **`stockwatch/`** — Flask server (`server.py`) exposed on `:5000` for open trades + transactions; `commands.py` registers `server start` into the live/simulate CLIs.
- **`utility/`** — framework helpers
  - `debug.py` — level-based logger (`dbg_trace/debug/info/warning/error/critical/log`) writing to per-day `log/<YYYYMMDD>/debug.log` and `journal.log`. `DebugSetting.setDbgPath()` must be called early (done by `investor.py`).
  - `config.py` — `BasicConfig` and `ConfigManager` base; `get_path(key)` joins against `path.root` and expands `~`; `get(key)` and `set(key, value, save=True)` use dot-notation.
  - `cli.py` — `CommandLineInterface` (raw REPL via `_Getch`) and `ArgParser` (tokenizer that supports `key:value` and `key=value`).
  - `utils.py` — `sleep_with_flag`, `sleep_until_with_flag` (interruptible sleeps that respect a `threading.Event`); `_Getch` for non-blocking single-char input.
  - `parallelprocessor.py` — thread-pool helper used by simulate/backtest.
  - `udb.py`, `log.py` — small DB/log helpers.

### Threading / process model
- **Live (`-m trade`)**: single process, 5 daemon threads orchestrated by `Core`. They cooperate via `TradingStatus.Trading.target_buying_list` (set by evaluation, drained by buying exec) and `next_wakeup_time` fields. All inter-service sleep uses `sleep_*_with_flag` so `stop_event` can break them.
- **Simulate (`-m simulate`)**: a separate `multiprocessing.Process` so `freezegun` can mock time inside it. The CLI process talks to it via `command_queue` and shared `Value`s. State is persisted to `path.broker/simulate/<timestamp>/` (set in `investor.py`).
- **Backtest / Test**: single-process, no long-lived threads.

### Configuration & paths
- `core/config.py` defines `AppConfig` with paths under `~/.config/investment/` (overridable via `cm.set('path.root', ...)`).
- The mode flag in `investor.py` rewrites `path.broker` before starting:
  - `-d` / `-m backtest` → `broker_development`
  - `-m test` → `broker_test`
  - `-m simulate` → `simulate/<timestamp>`
  - real trade (no flag) → `broker_<git_branch>` (falls back to `--broker` arg if not in a git repo)
- `Market.CACHED_DATA_PATH` is set from `path.data` and propagated to every provider.
- `DebugSetting.log_path` is set from `path.log` so daily log folders are created under it.

## Key Conventions

- The custom logger in `utility/debug.py` is used everywhere — prefer `dbg_info`/`dbg_warning`/`dbg_error` over `print` or `logging`.
- Config access goes through `AppConfigManager` (`cm.get`, `cm.set`, `cm.get_path`); mutate via dot-notation.
- All sleeps that block a service thread should use `sleep_with_flag` / `sleep_until_with_flag` so `stop_event` is honored.
- `BrokerManager.initialize(broker_type=...)` must be called before constructing `Trading`, `Simulate`, or any `BrokerManager()` instance. Both `Core.initialize` and `Simulate.__init__` do this.
- Order events flow through `BrokerManager` → `event_callback` → `BrokerManager.transaction_mgr.log_transaction` AND the registered `order_callback` (typically `Trading.order_callback`) which writes to `Recorder`.
- Strategy selection: prefer `Level.OFFICIAL` for production, `Level.BETA` for opt-in experiments, `Level.TESTING` only when the `test>0` flag is passed to `StrategyManager`.
- The README's `FIXME`/`TODO`/`Potential Risk` sections are the canonical list of known issues — consult them before introducing new fixes.

## Known issues worth keeping in mind
- `FIXME` items in `README.md` cover: hangs on missing-symbol `market.get_data`, insufficient-cash history failure, missing thread lock in backtest, thread-safety in strategy, broker reconnect on disconnect, sell-eval failure reporting, etc.
- `trading/traderecord.py` size inconsistencies can occur after manual broker intervention (see README's Potential Risk #1).
- `MockBroker` and `ShioajiBroker` differ in API surface — `core.py` still references `args.broker_type == 'mcok'` (typo) but the value is `'mock'`, so the branch is dead code; live trade always enters the warning branch.
- The git status shows `requirements.txt` is locally modified — verify any change to it before committing.
</content>
</invoke>