# Backtest

The `backtest/` package is a backtrader-driven historical backtester with a custom partial-trade analyzer, multiple backtest modes (default, year-roll, parameter optimization), and a `tabulate`-based result presenter.

## 1. Module Map

| File                          | Purpose                                                          |
|-------------------------------|------------------------------------------------------------------|
| `btcli.py`                    | `BTCLI` — the backtest CLI prompt.                               |
| `backtest.py`                 | `Backtest` — core engine wrapping backtrader's `Cerebro`.        |
| `backresult.py`               | `BackResult` — presentation layer (tables, charts).              |
| `datafeed.py`                 | `ExtPandasDataFeed` — pandas feed with `Turnover` line.          |
| `commands.py`                 | `register_backtest_commands` — global backtest config commands.  |
| `analyzer/partialtrade.py`    | `PartialTradeAnalyzer` — custom analyzer for partial fills.      |

## 2. `BTCLI` (`backtest/btcli.py`)

The main backtest CLI. Prompt: `backtest`. Manages the full backtest workflow through commands.

### `BacktestInfo` — data class

Holds the backtest configuration:

- `strategy_list` — list of strategy classes to test.
- `product_list` — list of symbols to test against.
- `mode` — `default` / `year` / `opt`.
- `from_date`, `to_date` — date range.
- `tune_params` — parameter grid for optimization mode.

Has `to_dict()`/`from_dict()` for JSON serialization.

### Commands

| Command       | Description                                                                                       |
|---------------|---------------------------------------------------------------------------------------------------|
| `info`        | Shows current configuration in a table.                                                           |
| `evaluate`    | Runs the backtest. Three modes:                                                                    |
|               | • `default`: iterates over each strategy and each product, running one backtest per combination. |
|               | • `year`: rolling 1-year windows shifted by 1 month, with 6 months warm-up before each window.    |
|               | • `opt`: grid search over strategy parameters using `cerebro.optstrategy`.                        |
| `report`      | Displays analysis results, annual returns, or draws plots.                                         |
| `data`        | Manages product list. Presets: `t5`/`t10`/`t20`/`t50`, `y20`/`y10`/`y05`/`y00`, `all`, `etf`, or individual codes. |
| `strategy`    | Manages strategy list: `set`, `add`, `del`, `list`, `tune`.                                         |
| `tune`        | Configures parameter grid for optimization mode (single value, range with step, or float range).  |
| `date`        | Sets date range with presets (`d1`-`d5` for 5-year windows, or explicit dates).                    |
| `mode`        | Switches between `default`, `opt`, and `year`.                                                     |
| `save_info` / `load_info` | Persists/restores `BacktestInfo` as JSON.                                              |
| `attr`        | Sets backtest attributes (e.g., `cash`).                                                           |

**Design pattern:** Command pattern via `regist_cmd`. The CLI delegates to `Backtest` and `StrategyManager`.

## 3. `Backtest` (`backtest/backtest.py`)

Core backtest engine wrapping Backtrader's `Cerebro`.

### Properties (with validation)

| Property         | Default      | Validation                                       |
|------------------|--------------|--------------------------------------------------|
| `init_cash`      | 1,000,000,000 | Positive numeric.                                |
| `commission`     | 0.001        | Non-negative numeric.                            |
| `slippage_prec`  | 0.001        | Non-negative numeric.                            |
| `from_date`      | None         | `datetime` or `None`.                            |
| `to_date`        | None         | `datetime` or `None`.                            |

### Methods

| Method                                                | Description                                                                                                |
|-------------------------------------------------------|------------------------------------------------------------------------------------------------------------|
| `setup(cerebro=None, broker=None)`                    | Creates/initializes `Cerebro`, sets up broker and analyzers. If `cerebro` is None, creates a new one.       |
| `add_symbol(product_list)`                            | Fetches market data via `Market.get_data()` and adds as `ExtPandasDataFeed` to Cerebro.                    |
| `add_data_frame(symbol_data_list)`                    | Alternative to `add_symbol` accepting pre-loaded DataFrames.                                                |
| `add_strategy(strategy_list)`                         | Adds strategies (standard).                                                                                 |
| `add_optstrategy(target_strategy, **kwargs)`          | Adds strategies for grid search optimization mode.                                                          |
| `add_history(order_history)`                          | Validates and adds historical orders (datetime, size, price, data_name tuples).                            |
| `eval()`                                               | Thread-safe (uses `_EVAL_LOCK`). Runs Cerebro, then calls `__analyze` to extract metrics.                  |
| `__analyze()`                                          | Extracts: annual return, Sharpe, VWR, drawdown, SQN, TradeAnalyzer, PartialTradeAnalyzer.                   |
| `save_report(report_path=None)`                       | Saves analysis CSV, annual returns CSV, plot images.                                                        |
| `show_drawing()` / `save_drawing(filepath)`           | Renders/saves Cerebro plots.                                                                               |

### `__analyze` — composite score

```python
score = 0.4 * VWR + 0.3 * (profit - drawdown) / 100 + 0.2 * Sharpe + 0.1 * SQN
```

This composite score is what `Evaluate` filters on (`score > 1` AND `sqn > 1.5`).

### Thread safety

Uses a per-`Backtest`-instance `_EVAL_LOCK` (`threading.Lock`). Different `Backtest` instances can run concurrently.

**Design pattern:** Facade over Backtrader's `Cerebro`.

## 4. `BackResult` (`backtest/backresult.py`)

Presentation layer for backtest results. Uses `tabulate` for formatted output.

### Methods

- `show_analysis(mode)` — displays a table with columns: Symbol, Strategy, Score, Profit, Sharpe, VWR, Max DD, SQN, Buys, Buy Win%, Sells, Sell Win%, Avg Duration. Modes: `all`, `average`, `mix`.
- `show_annual_return(mode)` — displays annual returns pivoted by year.
- `show_info()` — displays descriptions of each indicator.
- `_prepare_analysis_data(mode)` / `_prepare_annual_return_data(mode)` — internal grouping helpers.

**Surprising detail:** the "Sells" and "Sell Win%" columns come from the custom `PartialTradeAnalyzer` (pta), not from Backtrader's built-in `TradeAnalyzer`. The "Buys" and "Buy Win%" come from `TradeAnalyzer`. This split exists because `TradeAnalyzer` treats partial sells as separate trades, which would inflate trade counts and give misleading win rates.

## 5. `ExtPandasDataFeed` (`backtest/datafeed.py`)

Custom data feed that adds a `turnover` line. Maps columns: `Open`, `High`, `Low`, `Close`, `Volume`, `Turnover`. This is required by the `VWAP` indicator which uses `data.turnover` (not `close * volume`).

## 6. `PartialTradeAnalyzer` (`backtest/analyzer/partialtrade.py`)

Custom Backtrader analyzer that correctly tracks partial position sells. Backtrader's built-in `TradeAnalyzer` treats each partial sell as a separate trade, which inflates trade counts.

### Behavior

- Maintains a position dictionary per symbol (size, cumulative cost, average price).
- On buy: updates position with cost + commission.
- On sell: calculates PnL for the sold portion, records it as a trade, and decrements the position.

### `get_analysis(summary=True)`

Returns either:
- Per-symbol: `total`, `won`, `lost`, `pnl.net.total`, `pnl.net.average`, `trades` (list).
- Aggregated (when `summary=True`): overall `total`, `won`, `lost`, `pnl.net.total`, `pnl.net.average`, `trades`.

**Design pattern:** Observer (via Backtrader's `notify_order`). This is a critical component because without it, partial-fill strategies would report misleading win rates.

## 7. Commands Registration (`backtest/commands.py`)

Two functions:

- `register_backtest_commands(cli_ins)` — registers:
  - `config` (get/set/dump global config) — wraps `AppConfigManager` operations.
  - `backtest` (enter the `BTCLI`) — instantiates and runs `BTCLI`.

## 8. Usage Example

```bash
# From the backtest CLI:
backtest> mode default
backtest> data t5                       # use the 5-stock test set
backtest> strategy set MovingAverageCrossover
backtest> date d1                       # last 1 year
backtest> evaluate
backtest> report show analysis
backtest> report save plot             # saves PNG
```

## 9. Cross-Module Dependencies

```
backtest/btcli.py
  ├── backtest/backtest.py
  │     ├── backtest/analyzer/partialtrade.py
  │     ├── backtest/backresult.py
  │     ├── backtest/datafeed.py
  │     ├── strategy/strategy.py
  │     └── market/market.py
  └── backtest/commands.py
```

`Backtest` is also imported by `trading/evaluate.py` for the 1-year candidate analysis.
