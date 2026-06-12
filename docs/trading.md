# Trading Engine

The `trading/` package implements the evaluate/buy/sell lifecycle, trade recording, and the live-trading CLI.

## 1. Module Map

| File                       | Purpose                                                              |
|----------------------------|----------------------------------------------------------------------|
| `trading.py`               | `Trading` — the high-level orchestrator for buy/sell execution.       |
| `evaluate.py`              | `Evaluate` — strategy-driven candidate evaluation.                   |
| `traderecord.py`           | `Trade` and `Recorder` — open-trade lifecycle + persistence.         |
| `tradedata.py`             | SQLite schema and I/O for trades and transactions.                   |
| `tradecli.py`              | `TDCLI` — live-trading CLI (used by `Core`).                         |
| `commands.py`              | CLI command registration (trade/positions/transactions).             |

## 2. `Evaluate` (`trading/evaluate.py`)

Strategy-driven buy/sell candidate evaluation engine.

### Class constants

```python
BUY_CANDIDATE_SCORE_THRESHOLD = 1
BUY_CANDIDATE_SQN_THRESHOLD = 1.5
```

### `__init__()`

- Creates `StrategyManager` and `Market`.
- Loads official strategies via `StrategyManager.get_strategy_list([Level.OFFICIAL])`.
- Sets the first strategy as default.

### Buy evaluation (two-stage)

```
__buy_find_candidate(product_list)
  → for each product:
      for each strategy:
        run Backtest over 1 year
        if strategy emits 'buy' signal AND symbol not already a candidate:
          record (symbol → strategy)
          break  # first matching strategy wins
  → return dict {symbol: strategy}

__buy_filering_profitable_product(candidate_dict)
  → re-analyze each (symbol, strategy) over 1 year
  → extract: profit, sharpe, vwr, drawdown, sqn, score
  → sort by score descending
  → filter: score > 1 AND sqn > 1.5
  → return filtered dict

buying_evaluation(product_list)
  → chains the two stages
  → prints the final buying list with product metadata
  → returns the filtered dict
```

### Sell evaluation

```
__get_realtime_data_list(symbol)
  → takes latest market data DataFrame
  → appends/updates a row with the current BID price as OHLC
  → returns augmented DataFrame

__sell_find_candidate(position_dict)
  → for each held position:
      retrieve the trade record (if any) to get strategy name and buy history
      run the strategy's sell evaluation over 1 year with real-time-augmented data
  → return list of {symbol, size, price, strategy}

selling_evaluation(position_dict)
  → calls __sell_find_candidate
  → prints details
  → returns candidate list
```

## 3. `Trading` (`trading/trading.py`)

The high-level trading orchestrator. The integration point between evaluation, broker, and recorder.

### Class-level globals

```python
BUYING_IGNORE = False   # global kill switch for buys
SELLING_IGNORE = False  # global kill switch for sells
BUYING_CANDIDATE = {}   # shared map: symbol → strategy (used by order_callback)
```

### `__init__()`

Registers `self.order_callback` with `BrokerManager.set_order_callback`. This is how `Trading` hooks into the order event pipeline.

### `order_callback(event, data)`

On `Event.OrderFilled`:
1. Extract the strategy name from `BUYING_CANDIDATE` (for BUY) or fall back to the default strategy.
2. Call `Recorder.add_record()` to persist the transaction.

### `buying_exec(buy_list)`

For each candidate in `buy_list`:
1. Skip if already held.
2. Calculate lot size based on config: `LOT_UNIT`, `CASH_MAX_PER_TRADE`, `CASH_MIN_PER_TRADE`.
3. Get ASK price.
4. Compute affordable lot count: `order_lot = floor(buying_budget / (price * lot_unit))`.
5. Check against `CASH_MIN_PER_TRADE` (skip if order value below).
6. Place the order via `BrokerManager.place_order`.
7. After all buys, summarize positions.

### `selling_exec(selling_list)`

For each sell candidate:
1. Get BID price.
2. Check holding size from broker.
3. Handle three cases:
   - `selling_size == holding_size` → full close.
   - `selling_size < holding_size` → partial (with minimum-cash check that may trigger full close if remaining would be too small).
   - `selling_size > holding_size` → error case, sells all (capping at holding size).
4. After all sells, summarize positions.

### `trading_eval(args, product_list)`

Creates `Evaluate`, calls `buying_evaluation`, stores result in `BUYING_CANDIDATE` (so `order_callback` can later backfill the strategy name on actual fills).

### `selling_eval(args)`

Creates `Evaluate`, gets all positions from broker, calls `selling_evaluation`, returns result.

## 4. `Trade` and `Recorder` (`trading/traderecord.py`)

### `Trade` — buy-to-sell cycle

```python
Trade(symbol, action, price, size, timestamp, commission=0.0, strategy='')
```

- Generates a UUID `trade_id` on construction.
- Creates the first transaction and appends to `self.transactions` (list of dicts).
- `add_transaction(action, price, size, timestamp, commission)` — appends a new transaction dict.
- `is_open` (property) — `current_size > 0`.
- `current_size` (property) — `bought_total - sold_total`.
- `calculate_profit()` — for closed trades: `sum(sell_revenue) - sum(buy_cost) - sum(commission)`.

### `Recorder` — persistence adapter

```python
Recorder(data_path='')  # opens SQLite at {broker_path}/trade.db
```

Methods:
- `get_open_trades(symbol=None)` — fetches open trade info from DB, fetches all transactions, reconstructs `Trade` objects in memory.
- `get_records(symbol)` — convenience alias for `get_open_trades(symbol)`.
- `add_record(symbol, action, price, size, timestamp, commission, strategy)` — finds or creates an open `Trade` for the symbol. Appends transaction to existing open trade on BUY, starts a new one if no open trade exists, warns on SELL with no open trade. Calls `show_records` after each addition.
- `get_report(period='month')` — reconstructs closed trades, computes profit, groups by period (`day`/`week`/`month`/`year`), returns aggregated DataFrame.
- `show_report(period)` — prints `tabulate` output.
- `show_records(symbol, strategy, duration)` — prints all trades/transactions. Duration filter only shows trades with transactions in the window, **but always includes all open trades regardless of duration**.

**Important caveat:** the README flags size inconsistencies between broker and recorder after manual interventions (Potential Risk #1). This is a known issue.

## 5. `Database` (`trading/tradedata.py`)

SQLite schema:

```sql
CREATE TABLE Trades (
    trade_id TEXT PRIMARY KEY,
    symbol TEXT,
    strategy TEXT
);

CREATE TABLE Transactions (
    transaction_id TEXT PRIMARY KEY,
    trade_id TEXT REFERENCES Trades(trade_id),
    action TEXT,        -- 'BUY' or 'SELL'
    price REAL,
    size INT,
    timestamp INT,
    commission REAL
);
```

Methods:
- `setup_tables()` — creates both tables.
- `insert_trade(trade_id, symbol, strategy)`.
- `insert_transaction(trade_id, action, price, size, timestamp, commission)` — generates a UUID for `transaction_id`.
- `get_open_trades_info(symbol=None)` — JOINs Trades+Transactions, groups by `trade_id`, keeps only rows where `SUM(CASE WHEN action='BUY' THEN size ELSE -size END) > 0`.
- `get_closed_trades_info(symbol=None)` — same JOIN with `SUM = 0`.
- `get_transactions_for_trades(trade_ids)` — SELECT with `IN (...)` clause, ordered by timestamp ASC.
- `get_trades_info(symbol, strategy)` — conditional WHERE clauses.
- `get_trade_ids_by_transaction_time_range(start, end)` — DISTINCT trade_ids with transactions in a timestamp window.

**SQL safety note:** uses string interpolation (f-strings) for SQL construction, not parameterized queries. This is a potential SQL injection vector if symbol or strategy values are not sanitized. In practice they come from internal sources only.

## 6. `TDCLI` (`trading/tradecli.py`)

The live-trading CLI prompt (`TDCLI`).

### Construction

```python
TDCLI(promote='TDCLI')
```

- Creates a `Market` instance.
- Loads history path.
- Registers `trading_config` command and delegates to `register_trading_commands()` and `register_backtest_commands()`.

### `cmd_trade_config(args)`

Sets/views the `BUYING_IGNORE` and `SELLING_IGNORE` flags on the `Trading` class.

**Known bug:** the `print` statements on lines 45-46 and 52-53 use operator precedence incorrectly — `"buying " + "enable" if ... else 'disable'` evaluates as `("buying " + "enable") if ... else "disable"`, producing strings like `"buying enable"` instead of `"buying enabled"` or `"buying disabled"`.

## 7. CLI Commands (`trading/commands.py`)

Three commands registered via `register_trading_commands(cli_ins)`:

### `trade <subcommand>`

- `status [symbol=] [duration=]` — calls `Recorder.show_records()`.
- `report [period=]` — calls `Recorder.show_report()`.

### `positons` (typo preserved from source)

- `show` — calls `BrokerManager.summarize_positions()`.

### `transactions <period>`

- Period: `year`, `month`, `week`, `day` — calls `BrokerManager.summarize_transactions()`.

Each function is a standalone module-level function invoked by the CLI framework. `cmd_trade`, `cmd_positions`, and `cmd_transactions` each instantiate their own `Recorder` or `BrokerManager` locally.

## 8. End-to-End Buy/Sell Flow

```
1. Core.__trading_service (after market close)
   → Trading.trading_eval(args, product_list)
   → Evaluate.buying_evaluation(product_list)
     → __buy_find_candidate: identify (symbol, strategy) pairs
     → __buy_filering_profitable_product: filter by score/sqn
   → result stored in Trading.BUYING_CANDIDATE and trading_status.target_buying_list

2. Core.__trading_service (at next market open)
   → Trading.buying_exec(buying_list)
   → for each: calc lot, place_order → MockBroker → OrderTracker → OrderService
   → event fires → order_callback → Recorder.add_record

3. Core.__selling_service (10-min loop while market open)
   → Trading.selling_eval(args)
   → Evaluate.selling_evaluation(positions)
   → Trading.selling_exec(candidates)
   → for each: place_order(SELL) → same event pipeline
```
