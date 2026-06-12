# Core Orchestrator

The `core/` package contains the live-trading orchestrator (`Core`), the config schema (`AppConfig`), and a thin sqlite helper (`Database`).

## 1. `Core` (`core/core.py`)

The main class. Manages 4 background service threads + 1 heartbeat thread. Each thread runs a `while True` loop that sleeps until a calculated market-time event (market open, close, or data-update time) using `sleep_with_flag` / `sleep_until_with_flag`, allowing clean interruption via a shared `threading.Event` (`self.stop_event`).

### Construction

```python
core = Core()
```

Sets:
- `flag_core_running`, `flag_trade_service_running`, etc. — boolean flags indicating service health.
- `self.threads` — list of `threading.Thread` references.
- `self.stop_event` — `threading.Event` shared by all services.
- `self.trading_status` — `TradingStatus` instance (cross-thread state).

### `initialize(broker_type="mock")`

Sets up the full dependency graph:
1. `AppConfigManager` (already loaded by `investor.py`).
2. `BrokerManager.initialize(broker_type)` — **must** be called before anything else broker-related.
3. `Market` (creates the `FindMind`/`TWSE`/`Yahoo` provider list).
4. `Trading` (registers `self.order_callback` with `BrokerManager.set_order_callback`).
5. `TDCLI` (live-trading prompt) with commands registered.

### `start()`

Launches all 5 threads (data source, trading, selling, broker, heartbeat), waits for them to report running, then enters the CLI event loop via `self.tdcli.run()`.

### `stop()` / `finalize()`

Sets all flags to `False`, sets `self.stop_event` (which interrupts any in-progress `sleep_with_flag` calls), joins all threads, and calls `BrokerManager.finalize()`.

### `cmd_status()`

Pretty-prints service states and next-wakeup times using `tabulate`. Reads from `self.trading_status` to show the target buying list. **Note**: `TradingStatus` uses plain class-level lists without a lock, so concurrent reads from the CLI while a service is writing may show partial state.

## 2. The 5 Service Threads

Each service follows the same pattern: a `while True` loop that checks its `flag_*_running` flag, sleeps until the next market event, then runs its work and re-sleeps.

### `__datasource_service`

Calls `Market.update_data()` at each `MARKET_UPDATE_TIME` (default: 18:00). If the date is a non-trading day, the update returns a date object and `MarketTime` records it.

### `__trading_service`

Runs after market close:
1. Calls `Trading.trading_eval(args, product_list)` — populates `trading_status.target_buying_list` and the `Trading.BUYING_CANDIDATE` map (used by `order_callback` to backfill strategy names).
2. Sleeps until next market open.
3. At market open, calls `Trading.buying_exec(trading_status.target_buying_list)`.

### `__selling_service`

Intra-day 10-min loop while market is open:
1. Sleeps 10 min (`sleep_with_flag`).
2. Calls `Trading.selling_eval(args)` then `Trading.selling_exec(candidates)`.
3. Continues until market close, then sleeps until next day's open.

### `__broker_service`

Reconnect / position summary around market open and close. Calls `BrokerManager.reconnect()` on disconnect and prints position summaries.

### `__heatbeat_service`

Sanity checks: calls private `_Core__sanitycheck()` which returns `True` only if all four service flags are `True`. Logs warnings on heartbeat.

## 3. `TradingStatus` (Nested Class in `Core`)

A simple namespace class that holds cross-thread state:

```python
class TradingStatus:
    target_buying_list = []  # set by trading service, drained by buying exec
    next_wakeup_time = {     # per-service next wake time
        'datasource_service': None,
        'trading_service': None,
        'selling_service': None,
        'broker_service': None,
    }
```

**Concurrency caveat**: `target_buying_list` is a plain Python list, not a thread-safe queue. The trading service writes to it; the CLI's `cmd_status()` reads it. Under heavy load, the CLI may observe a partial list. In practice the trading service finishes populating before the CLI is invoked, so this is rare.

## 4. `AppConfig` & `AppConfigManager` (`core/config.py`)

See [configuration.md](./configuration.md) for the full schema and mode-specific path rewrites.

`AppConfig` is a class-based config schema with four nested classes (`about`, `debug`, `path`, `stock`).

`AppConfigManager` is a `ConfigManager` subclass that:
- Overrides `path.root = "~/.config/investment"`.
- Exposes dot-notation `get`/`set`/`get_path` operations.
- Auto-saves to JSON on every `set` (unless `save=False`).

## 5. `Database` (`core/database.py`)

A thin SQLite wrapper extending `utility/udb.py:uDatabase`. Creates a `ProductTracking` table:

| Column      | Type |
|-------------|------|
| ID          | INTEGER PRIMARY KEY |
| ProductID   | TEXT |
| Tracking    | INTEGER (0/1) |
| Type        | TEXT (STOCK/ETF) |
| Name        | TEXT |
| Market      | TEXT (listed/otc/emerging) |
| Country     | TEXT |
| Category    | TEXT |
| Start       | TEXT |

### Methods

- `setup_tables()` — creates the table on first use.
- `add_product(productid, producttype, name, market, country, category, start, tracking)` — raises on duplicate.
- `update_tracking_product(productid, tracking)` — toggles the tracking flag; raises if product not found.
- `get_tracking_product()` — returns all tracked ProductIDs.

### Status

`Core.initialize()` has the database initialization **commented out** in the current source. The `Database` class is essentially unused at runtime; product tracking is not enforced. This is a known gap.
