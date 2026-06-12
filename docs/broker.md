# Broker Layer

The `broker/` package implements a multi-layer order management system with a pluggable broker architecture, event-driven order lifecycle tracking, transaction logging, and safety checks.

## 1. Architecture Overview

```
┌──────────────────┐
│ Trading          │  ← strategy evaluation produces orders
│   (trading.py)   │
└──────┬───────────┘
       │ place_order()
       ▼
┌──────────────────┐    class-level
│ BrokerManager    │    Lock + state
│ (singleton)      │
└──────┬───────────┘
       │ delegates to
       ▼
┌──────────────────┐
│ Broker           │  MockBroker or ShioajiBroker
│ (BaseBroker)     │  + order_checker() + OrderChecker.check()
└──────┬───────────┘
       │ creates
       ▼
┌──────────────────┐
│ OrderTracker     │  ← returned from place_order()
│ (dataclass)      │
└──────┬───────────┘
       │ passed to
       ▼
┌──────────────────┐
│ OrderService     │  polls every 1 sec, fires Event
│ (Thread)         │
└──────┬───────────┘
       │ callback
       ▼
┌──────────────────┐  ┌──────────────────┐
│ TransactionMgr   │  │ Trading          │
│ (CSV log)        │  │ (Recorder)       │
└──────────────────┘  └──────────────────┘
```

## 2. Constants & Enums

### `broker/order/constant.py`

```python
class OrderAction(Enum):
    BUY, SELL, UNKNOWN

class OrderStatus(Enum):
    FILLED, PARTIALLY_FILLED, PENDING_SUBMIT, PENDING_CANCEL,
    PRE_SUBMITTED, SUBMITTED, CANCELLED, EXPIRED, REJECTED, INACTIVE, UNKNOWN

class OrderPrice(Enum):
    BID, ASK, LAST
```

`None` is used to indicate a market order at the broker level (a `MARKET` enum value is commented out).

### `broker/order/event.py`

```python
class Event(Enum):
    OrderFilled, OrderFailed, OrderPending, OrderCanceled
```

## 3. `OrderTracker` (`broker/order/ordertracker.py`)

The universal order status container that flows through the entire event pipeline.

```python
@dataclass
class OrderTracker:
    timestamp: datetime
    symbol: str
    action: OrderAction
    size: int
    price: float
    status: OrderStatus
    reason: Optional[str]
    commission: Optional[float]
    order_instance: Any = field(...)  # links to broker-specific order object
```

- `order_instance` is **excluded from `__init__` and `__repr__`**, but is critical: `update_order_status()` copies fields from this linked object.
- `__post_init__()` coerces `timestamp` to `datetime` if a string was passed (for `from_dict` round-trips).
- `to_dict()` / `from_dict(data)` — ISO timestamps and enum `.value` strings.
- `show_order(title)` — pretty-prints as a `tabulate` grid.

## 4. `OrderService` (`broker/order/orderservice.py`)

A polling background thread that monitors active orders.

```python
class OrderService(threading.Thread):
    def __init__(broker_ins, event_callback=None)
    def add_order(order_tracker)
    def run()        # main loop
    def stop()
```

- `add_order` performs an **immediate status check** on insertion: if already `FILLED`, fires `Event.OrderFilled`; if in a terminal failure state (`CANCELLED`/`REJECTED`/`EXPIRED`/`INACTIVE`), fires `Event.OrderFailed`. Otherwise appends to `active_orders` for polling.
- The `run()` loop iterates `active_orders`, calls `broker_ins.update_order_status(order_tracker)`, and fires events on state transitions. Sleeps 1 second between iterations.
- This polling-with-immediate-check pattern is why mock/fast-fill orders are processed synchronously without waiting for the next poll.

## 5. `OrderChecker` (`broker/order/checker.py`)

A static "second safety" checker, distinct from each broker's own `order_checker()` instance method.

```python
class OrderChecker:
    CASH_LIMIT_PER_ORDER = AppConfig.stock.cash_max_per_trade * 2  # 20000 by default

    @staticmethod
    def check(action, price, size) -> bool:
        # raises ValueError if price * size > CASH_LIMIT_PER_ORDER for BUY
```

Both checks run in sequence inside `BaseBroker.place_order()`.

## 6. `BrokerManager` (`broker/brokermanager.py`)

The central orchestrator. Built almost entirely on **class-level state** (a Singleton via class variables).

### Class-level state

```python
class BrokerManager:
    broker = None              # the active Broker instance
    order_svc = None           # OrderService instance
    transaction_mgr = None     # TransactionManager
    _broker_connected = False
    _lock = threading.Lock()   # shared across all instances
    order_callback = None      # set via set_order_callback()
    broker_path = ""           # where to persist state
```

### `initialize(broker_type='mock', **kwargs)` (classmethod)

**The one-time setup entry point.** Must be called before any other method (the `Core.initialize` and `Simulate` both do this).

Steps:
1. Create `MockBroker(broker_path=...)` or `ShioajiBroker(**kwargs)`.
2. Create `TransactionManager(broker, lock, transaction_log_path)`.
3. Create `OrderService(broker_ins, event_callback)`.
4. Call `broker.connect()`.
5. Set `_broker_connected = True`.
6. Start `order_svc` thread.

### `lock(timeout=10.0) -> bool`

Acquires the class-level `threading.Lock` with a 10-second timeout, then **immediately calls `broker.check_quota()`** — so quota failures release the lock. Logs caller stack info via `inspect` for traceability.

This is the canonical "enter critical section" pattern. All `BrokerManager` instance methods (place_order, get_balance, etc.) wrap their work in `lock`/`unlock`.

### `reconnect()` (classmethod)

Retries broker disconnect/connect up to 5 times with 10-minute delays. Used by the broker service thread.

### `finalize()` (classmethod)

Calls `order_svc.stop()`, `broker.disconnect()`, clears all class-level state.

### Instance methods (all thread-safe via `lock`/`unlock`)

- `place_order(symbol, action, size, price=None)` — accepts deprecated strings `'buy'`/`'sell'`/`'BUY'`/`'SELL'` and converts them silently.
- `get_balance()` / `get_position_by_symbol(symbol)` / `get_all_positions()` / `get_last_price(symbol, price_type)` / `get_portfolio_value()`.
- `summarize_positions()` — prints a formatted `tabulate` table of all positions with market values and unrealized P&L.
- `set_state_filepath(filepath)` — for `MockBroker` state persistence.

### Module-level `event_callback(event, data)`

The default callback attached to `OrderService`. Type-checks that `data` is an `OrderTracker`, dispatches to `BrokerManager.order_callback` (if set by a higher layer like `Trading`), and for `OrderFilled` events, calls `TransactionManager.log_transaction()`.

This is the integration point between order execution and transaction logging.

## 7. Broker Implementations

### `BaseBroker` (`broker/brokers/base/basebroker.py`)

Abstract interface. Abstract methods: `connect()`, `disconnect()`, `check_quota()`, `get_balance()`, `get_all_positions()`, `get_position_by_symbol()`, `get_portfolio_value()`, `get_last_price()`, `order_checker()`, `update_order_status()`, `place_order()`.

The `place_order` template in the base class includes the dual safety-check logic. Both `MockBroker` and `ShioajiBroker` end up running both checks (once in their own `order_checker()`, once via `OrderChecker.check()`).

### `Position` (`broker/brokers/base/position.py`)

Plain data container:

```python
@dataclass
class Position:
    symbol: str
    size: int
    average_entry_price: float
    initial_entry_price: float
    open_date: datetime
```

`update(action, size, price)` mutates size and average price. On first buy, captures `initial_entry_price` and `open_date`. On sell, reduces size and resets averages to zero when position closes.

### `MockBroker` (`broker/brokers/mock/mockbroker.py`)

Fully functional simulated broker for development and testing.

**Construction:**
```python
MockBroker(initial_cash, commission_rate=0.003, simulation=True, **kargs)
```

- Creates a `Market` + `TWSE` provider.
- Stores `Position` dict keyed by symbol.
- Sets `cash_limit_per_trade` from `AppConfig.stock.cash_max_per_trade`.

**Key behaviors:**

- `is_market_open()`: in simulation mode always returns `True`; in live mode checks TWSE hours (Mon–Fri 9:00–13:25).
- `check_quota()`: always returns `True`.
- `place_order(...)`: full simulation execution — checks market open, retrieves market price, enforces limit price conditions, runs both safety checkers, validates cash (BUY) or position size (SELL), updates cash and positions, creates `MockOrder` and `OrderTracker`, **saves state to JSON**. Returns the `OrderTracker` on all paths (filled OR rejected), never `None` for valid input.
- `get_last_price(symbol, price_type)`: in simulation, reads the last `Close` from historical data filtered to `<= today`. In live mode, delegates to `TWSE.get_current_price`.
- `get_portfolio_value()`: sums cash + position values using `get_last_price`.

**State persistence:** JSON at `{broker_path}/positions.json`, saved on every executed order. `_load_position_state` has thorough deserialization guards (missing keys, symbol mismatch, zero/negative size).

### `ShioajiBroker` (`broker/brokers/shioaji/shioajibroker.py`)

Real broker implementation for the Taiwan Shioaji API (永豐金證券).

**Status: simulation-only.** `__init__` currently forces `simulation=True` unconditionally; real trading raises `NotImplementedError`. `get_balance()` in simulation returns a fixed $10,000.

**Odd-lot trading:** Defaults to `_is_lot_trade = False` (odd-lot trading via `__place_order_odd`). Lot trading is not implemented.

**Realtime price via WebSocket:** `__get_last_price_odd` subscribes to tick-level odd-lot quotes via Shioaji's WebSocket API, uses a `queue.Queue` with a 3-second timeout, and returns `tick.close`. Unsubscribes in `finally` block. **This means `get_last_price` will block for up to 3 seconds.**

**Quota checks:** `check_quota` blocks login if remaining bytes < 20 MB; warns if < 50 MB.

**Order placement:** `__place_order_odd` fetches the contract, creates a `StockPriceType.LMT` / `OrderType.ROD` / `StockOrderLot.IntradayOdd` order, places via Shioaji API, and creates an `OrderTracker` from the returned `Trade` object.

**Note:** Lines 576-580 contain a dead-code path where `return None` appears after `dbg_error` and before the actual order placement logic, which means any non-BUY/SELL action returns `None` early.

### `MockOrder` (`broker/brokers/mock/mockorder.py`)

```python
@dataclass
class MockOrder:
    event_type: Event
    timestamp: datetime
    symbol: str
    action: OrderAction
    size: int
    price: float
    commission: float
    status: OrderStatus
    reason: Optional[str]
```

Structurally parallel to `OrderTracker` but additionally carries `event_type`. Acts as the "source of truth" for `MockBroker.update_order_status` pattern.

## 8. `TransactionManager` (`broker/transaction.py`)

CSV-backed transaction log and P&L engine.

**Storage:** `{broker_path}/transaction.csv` with header: `timestamp, symbol, action, size, price, commission, cash_balance`.

**Methods:**

- `__init__(broker, lock, transaction_log_path)` — creates log directory, writes header if file doesn't exist, logs existing broker positions as `initial` rows.
- `log_transaction(symbol, action, size, price, commission, cash_balance)` — appends one row.
- `get_transactions()` — reads all rows via `csv.DictReader`.
- `get_summary_data(duration)` — computes per-symbol and aggregate P&L for a period (`day`/`week`/`month`/`year`/`all`). Uses **COGS-based P&L with FIFO-like averaging** (tracks cost basis continuously across periods, not simple per-period averages).
- `summarize_transactions(duration)` — prints formatted `tabulate` output.

The `_log_transaction_init` method runs inside the shared `BrokerManager._lock` to prevent races during initialization.

## 9. Order/Event Flow End-to-End

```
1. Trading.trading_eval() / .selling_eval()
   → calls Evaluate.buying_evaluation() / .selling_evaluation()
   → uses Backtest + strategies to generate candidate lists

2. Trading.buying_exec() / .selling_exec()
   → iterates candidates, calculates lot size
   → calls BrokerManager.place_order()

3. BrokerManager.place_order()
   → acquires class-level lock
   → calls BrokerManager.broker.place_order() (e.g., MockBroker)
   → MockBroker runs dual safety checks, executes, returns OrderTracker

4. OrderService.add_order(order_tracker)
   → immediate status check; fires Event if terminal
   → else: appended to active_orders

5. OrderService.run() (background thread, 1 sec poll)
   → calls broker.update_order_status(order_tracker)
   → fires events on state transitions

6. Events dispatch to event_callback chain:
   → module-level event_callback in brokermanager.py
     (logs to TransactionManager)
   → then Trading.order_callback()
     (records to Recorder / SQLite)
```

## 10. Usage Example

```python
from broker.brokermanager import BrokerManager

# Initialization (must be called first)
BrokerManager.initialize(broker_type='mock', initial_cash=1000000)

# Lock-based critical section
if BrokerManager().lock():
    try:
        order = BrokerManager().place_order(
            symbol='2330',
            action='buy',
            size=1000,
            price=None,  # market order
        )
        # order is an OrderTracker (filled or rejected, never None for valid input)
    finally:
        BrokerManager().unlock()

# Cleanup
BrokerManager.finalize()
```
