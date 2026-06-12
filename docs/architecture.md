# Architecture

This document describes TradeBot's high-level architecture: how the four execution modes are dispatched, the threading/process model, the order/event flow, and the cross-module dependency graph.

## 1. Entry Point and Mode Dispatch

`investor.py` is the single entry point. It:

1. Parses CLI flags (mode, broker type, product list, time-frame).
2. Builds an `AppConfigManager` and loads `~/.config/investment/config.json` (or `path.root`-relative `config.json`).
3. Sets `DebugSetting.setDbgPath(cm.get_path('log'))` for the custom logging subsystem.
4. **Rewrites `path.broker` based on the mode** (this is the canonical mode switch — see [configuration.md](./configuration.md#mode-specific-path-rewrites)):
   - `-d` (development) → `broker_development`
   - `-m test` → `broker_test`
   - `-m backtest` → `broker_development`
   - `-m simulate` → `simulate/<timestamp>`
   - default (real trade) → `broker_<git_branch>` (with explicit `yes` confirmation prompt)
5. Calls `setup_matplot()` (configures WebAgg backend on port 8888 for plot viewing).
6. Dispatches to one of four sub-CLIs based on `--trade-mode`:

| Mode        | Flag           | Class            | Process Model                          |
|-------------|----------------|------------------|----------------------------------------|
| `trade`     | (default)      | `Core`           | Single process, 5 threads              |
| `simulate`  | `-s`           | `SimulateCLI`    | CLI process + 1 child process          |
| `backtest`  | `-b`           | `BTCLI`          | Single process, no long-lived threads  |
| `test`      | `-t`           | `TestCLI`        | Single process, no long-lived threads  |

On exit, `cm.save()` persists any config changes.

## 2. Threading & Process Model

### Live Trading (`-m trade`)

`Core` spawns 5 long-lived daemon threads:

| Thread               | Responsibility                                                                                                |
|----------------------|---------------------------------------------------------------------------------------------------------------|
| `datasource_service` | Refreshes market data via `Market.update_data()` at market-update times.                                      |
| `trading_service`    | Runs strategy evaluation after market close; populates `target_buying_list`; executes buys at next open.       |
| `selling_service`    | Intra-day 10-min loop while market is open; evaluates sells and executes.                                     |
| `broker_service`     | Reconnect / position summary around market open and close.                                                    |
| `heatbeat_service`   | Sanity check loop.                                                                                            |

Cross-thread state lives in a `TradingStatus` namespace (next wake-up times, target buying list). All inter-service sleeps use `sleep_with_flag` / `sleep_until_with_flag` so `stop_event` can break them.

### Simulate (`-m simulate`)

`Simulate` extends `multiprocessing.Process`. The CLI process talks to it via:
- `command_queue` (`multiprocessing.Queue`) for buy/sell/positions/etc.
- Shared `Value`s and `Event` for `pause` / `continue` and time advancement.
- `freezegun` mocks wall time **inside** the child process only.

This separation is required because `freezegun` only mocks time for the process that calls it; running the simulator in the same process as the CLI would freeze the CLI as well.

State is persisted under `path.broker = "simulate/<timestamp>"`.

### Backtest / Test

Single-process, no long-lived threads. Backtest uses a per-`Backtest`-instance `_EVAL_LOCK` to allow concurrent backtest evaluations on different instances.

## 3. Order / Event Flow

The end-to-end order lifecycle:

```
Evaluate.buying_evaluation() / .selling_evaluation()
   ↓ produces candidate list
Trading.buying_exec() / .selling_exec()
   ↓ iterates candidates, calculates lot size
BrokerManager.place_order(symbol, action, size, price)
   ↓ acquires class-level lock + check_quota()
Broker.place_order() (MockBroker or ShioajiBroker)
   ↓ runs dual safety checks (self.order_checker + OrderChecker.check)
   ↓ executes, creates OrderTracker
OrderService.add_order(order_tracker)
   ↓ if terminal state on insertion: fires Event immediately
   ↓ else: appended to active_orders for polling
OrderService.run() (background thread)
   ↓ polls active_orders every 1 second
   ↓ calls broker.update_order_status(order_tracker)
   ↓ fires Event on state transitions
event_callback(event, data)  ← BrokerManager default
   ↓ dispatches to BrokerManager.order_callback
   ↓ for OrderFilled: TransactionManager.log_transaction()
   ↓ then: Trading.order_callback() ← registered at Trading.__init__
            → Recorder.add_record() → SQLite persistence
```

### Event Types

Defined in `broker/order/event.py`:

- `Event.OrderFilled` — terminal success
- `Event.OrderFailed` — terminal failure (rejected, cancelled, expired, inactive)
- `Event.OrderPending` — order is in a non-terminal state
- `Event.OrderCanceled` — order was cancelled

### Order Status

Defined in `broker/order/constant.py:OrderStatus`:

- `FILLED`, `PARTIALLY_FILLED`
- `PENDING_SUBMIT`, `PENDING_CANCEL`, `PRE_SUBMITTED`, `SUBMITTED`
- `CANCELLED`, `EXPIRED`, `REJECTED`, `INACTIVE`
- `UNKNOWN`

## 4. Cross-Module Dependency Graph

```
investor.py
   ├── core.core (Core)
   │     ├── core.config (AppConfigManager)
   │     ├── core.database (Database, mostly unused)
   │     ├── market.market (Market facade)
   │     ├── broker.brokermanager (BrokerManager)
   │     ├── trading.trading (Trading, Recorder)
   │     ├── trading.tradecli (TDCLI)
   │     ├── trading.evaluate (Evaluate)
   │     ├── strategy.strategy (StrategyManager)
   │     └── stockwatch.commands (server registration)
   │
   ├── backtest.btcli (BTCLI)
   │     ├── backtest.backtest (Backtest engine)
   │     │     ├── backtest.analyzer.partialtrade (PartialTradeAnalyzer)
   │     │     ├── backtest.backresult (BackResult presentation)
   │     │     ├── backtest.datafeed (ExtPandasDataFeed)
   │     │     └── strategy.strategy
   │     └── backtest.commands
   │
   ├── simulate.simulatecli (SimulateCLI)
   │     └── simulate.simulate (Simulate, multiprocessing.Process)
   │           ├── trading.trading
   │           ├── trading.traderecord (Recorder)
   │           └── broker.brokermanager
   │
   ├── testutility.testcli (TestCLI)
   │     ├── testutility.core
   │     ├── testutility.market
   │     ├── testutility.trading
   │     ├── testutility.broker
   │     ├── testutility.backtest
   │     └── testutility.integration
   │
   └── stockwatch (Flask server, registered as CLI command in TDCLI)
```

All packages depend on `core.config.AppConfigManager` and `utility.debug` (custom logging).

## 5. Data Flow Summary

| Stage             | Where it lives           | Format / Storage                                  |
|-------------------|--------------------------|---------------------------------------------------|
| Config            | `~/.config/investment/`  | JSON (`config.json`)                              |
| Market data cache | `path.data`              | CSV, organized by provider name                   |
| Product list      | `Market.cached_stock_info_frame` | In-memory DataFrame                       |
| Trade DB          | `path.broker/trade.db`   | SQLite (schema in `trading/tradedata.py`)         |
| Order state       | `path.broker/positions.json` | JSON (MockBroker persistence)                  |
| Transactions      | `path.broker/transaction.csv` | CSV                                  |
| Backtest reports  | `path.bt_report`         | PNG plots + CSVs                                  |
| Simulation state  | `path.broker/simulate/<timestamp>/` | JSON                        |
| Debug logs        | `path.log/<YYYYMMDD>/`   | `debug.log`, `journal.log`                        |

## 6. Key Design Patterns

- **Singleton via class-level state** — `BrokerManager` holds its broker, order service, and lock as class-level attributes. Multiple instances share the same underlying broker.
- **Facade** — `Market` is a facade over multiple data providers; `BrokerManager` is a facade over the broker interface.
- **Template Method** — `BasicExitStrategy` defines `stra_initial()` / `stra_buy_in()` / `stra_sell_out()` as virtual methods; concrete strategies fill them in.
- **Observer** — `OrderService` polls orders and fires `Event` callbacks; Backtrader's `notify_order` / `notify_trade` notifies strategies; `OrderTracker` and `Trade` collect event data.
- **Strategy Registry** — `StrategyManager` registers classes under three `Level`s (`OFFICIAL` / `BETA` / `TESTING`), controlling which strategies are loaded for a given mode.
- **Event-driven state machine** — Order events (`OrderFilled`/`OrderFailed`/`OrderPending`/`OrderCanceled`) flow through the order pipeline; `OrderService` is the central dispatcher.
- **Context-based config** — `ConfigManager` uses nested Python classes (not dicts) to define a typed config schema.
