# Testing Framework

TradeBot uses a **custom CLI-driven test runner** (not `pytest` or `unittest`). Tests are organized into six groups (`core`, `market`, `trading`, `broker`, `backtest`, `integration`) and executed from the `TestCLI` prompt.

## 1. TestCLI (`testutility/testcli.py`)

### `TestCLI(CommandLineInterface)`

The test entry point. Prompt: `test`.

#### Commands

| Command     | Test group      | File                                |
|-------------|-----------------|-------------------------------------|
| `core`      | Core            | `testutility/core.py`               |
| `market`    | Market          | `testutility/market.py`             |
| `trading`   | Trading         | `testutility/trading.py`            |
| `broker`    | Broker          | `testutility/broker.py`             |
| `backtest`  | Backtest        | `testutility/backtest.py`           |
| `integration` | Integration   | `testutility/integration.py`        |
| `test`      | Run all         | (delegates to the above)            |

Each test command accepts a list of test names or `"all"`. Results are printed as a colored `tabulate` table with `total`/`passed`/`failed` counts.

### Usage

```bash
$ python investor.py -t

test> broker                    # run all broker tests
test> market all                # run all market tests
test> broker test_initial_state test_place_buy_order_sufficient_cash
test> test                      # run all test groups
```

## 2. Test Suite Format

Each test module follows the same pattern:

```python
# 1. Per-test functions
def test_xxx(test_id: str) -> bool:
    # test logic
    return True   # pass
    # or return False / raise

# 2. Name → function mapping
SUITE_TEST_DEFINITIONS = {
    'test_xxx': test_xxx,
    # ...
}

# 3. Test case list (includes "all")
SUITE_TEST_CASES = list(SUITE_TEST_DEFINITIONS.keys()) + ['all']

# 4. Runner
def run_xxx_tests(test_names: list[str]) -> dict:
    total, passed, failed = 0, 0, 0
    for name in test_names:
        total += 1
        try:
            if SUITE_TEST_DEFINITIONS[name]():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
    return {'total': total, 'passed': passed, 'failed': failed}
```

`TestCLI.cmd_test()` aggregates results from all groups into a single colored table.

## 3. Test Suite Summaries

### `testutility/core.py` (7 tests)

Tests the `Core` class and its services. Uses `unittest.mock.patch` to mock `sleep_with_flag`, `sleep_until_with_flag`, market time methods, and internal service methods. **Tests directly access private methods** (e.g., `_Core__sanitycheck`, `_Core__datasource_service`) using Python name mangling.

| Test                               | Description                                                                       |
|------------------------------------|-----------------------------------------------------------------------------------|
| `test_core_initialization`         | Verifies `Core` instantiation, `initialize()`, and all running flags are initially `False`. Checks `trading_status` is a `TradingStatus` instance. |
| `test_core_start_and_stop_flow`    | Starts `Core` in a separate thread with mocked internals. Verifies all service flags become `True` on start, `False` on stop. |
| `test_core_sanity_check_method`    | Tests private `_Core__sanitycheck()` by setting/clearing the five running flags. |
| `test_cmd_status_output`           | Mocks `Market.get_data_info` and `datetime`, captures `cmd_status()` stdout, asserts specific formatted output lines including service status and target buying list (2330, 2454). |
| `test_datasource_service_loop_and_update` | Runs `_Core__datasource_service` in a thread with mocked market time. Verifies `__update_datasource` is called and `next_wakeup_time` resets to `None`. |
| `test_trading_service_flow`        | Runs `_Core__trading_service` in a thread with mocked market time, `trading_eval` returning `['2330']`, and `buying_exec`. Verifies `buying_exec` is called with `['2330']`. |
| `test_selling_service_flow`        | Similar pattern for the selling service.                                          |

### `testutility/market.py` (8 tests)

Integration-style tests against the live market providers. `get_markget_list()` (typo preserved from source) is the only Market method that doesn't need a real provider.

| Test                          | Description                                                                |
|-------------------------------|----------------------------------------------------------------------------|
| `test_list_providers`         | Verifies `get_markget_list()` returns a non-empty list.                    |
| `test_switch_market`          | Cycles through available providers, verifies switch, then restores.        |
| `test_get_data_list`          | Verifies `get_data_list()` updates `cached_stock_info_frame`.              |
| `test_get_data`               | Fetches 365 days of `2330` (TSMC) data, verifies OHLCV columns.            |
| `test_get_data_info`          | Fetches `2330` info, verifies dict keys (`code`, `name`, `start`, `market`). |
| `test_get_top_product_list`   | Tests default (50), specific (10), and capped (100 → 50) counts.            |
| `test_get_product_list_by_date` | Tests date filtering at `2022-01-01` and `1990-01-01`; earlier dates return more symbols. |
| `test_update_data`            | Tests `update_data()` with `force_update=False` and `force_update=True`.   |

### `testutility/trading.py` (8 tests)

The largest and most complex test file. Uses extensive `unittest.mock` to isolate the `Trading` and `Evaluate` classes.

| Test                              | Description                                                                                |
|-----------------------------------|--------------------------------------------------------------------------------------------|
| `test_buying_evaluation`          | Mocks `Market.get_data_list` returning `['2330', '2454']`, runs `Evaluate.buying_evaluation()`. |
| `test_selling_evaluation`         | Initializes `BrokerManager` with mock, creates `Evaluate` with two `MockPosition` entries, runs `selling_evaluation()`. |
| `test_trading_buying_exec`        | Mocks `AppConfigManager` and `BrokerManager`. Tests four scenarios: empty list, valid buy (verifies lot calculation), zero-lot, and order value below `CASH_MIN_PER_TRADE`. |
| `test_trading_selling_exec`       | Tests five scenarios: empty list, valid sell (size ≤ holding), oversell (size > holding), partial with remaining value below minimum (sells all), partial with remaining value above minimum (sells expected size). |
| `test_trading_trading_eval_flow`  | Mocks Market, Analyzer, StrategyManager. Verifies `trading_eval()` returns a dict keyed by `DEFAULT_TEST_TICKER` with `strategy`, `profit`, `sharpe`, `vwr`, `drawdown`, `sqn`, `score` keys. |
| `test_trading_order_callback`     | Mocks `Recorder`, `datetime`, `OrderTracker`, `isinstance`. Verifies `OrderFilled` event triggers `Recorder.add_record`; `OrderFailed` does not. |
| `test_trading_selling_eval_flow`  | Mocks `Evaluate` and `BrokerManager.get_all_positions`. Verifies `selling_eval()` returns the mocked list. |
| `test_recorder_save_and_load`     | The only test using a real database file (via `tempfile`). Tests five scenarios: new DB init, add record and verify persistence, sell with no open position, load into new `Recorder` instance and verify (AAPL partial, GOOG full close, NVDA buy-only), cross-instance persistence. |

### `testutility/broker.py` (14 tests)

The most test cases in any file. Tests the full broker lifecycle with `MockBroker` and `TransactionManager`.

Setup helper: `_setup_test_broker_manager(test_name, initial_cash, commission_rate, state_filepath, transaction_log_path, clean_file)` creates temp state and transaction log files, sets `stock.cash_max_per_trade = 100000`, and calls `BrokerManager.initialize(broker_type='mock', simulation=True)`. Teardown helper: `cleanup_test_broker_files(test_name)` deletes the test files.

| Test                                          | Description                                                                              |
|-----------------------------------------------|------------------------------------------------------------------------------------------|
| `test_initial_state`                          | Verifies initial cash and empty positions.                                               |
| `test_place_buy_order_sufficient_cash`        | Buys 5 shares of `2330`, verifies transaction log, cash reduction, position size, average entry price. |
| `test_place_buy_order_insufficient_cash`      | Cash $10, tries 100-share buy, verifies no change and no transaction.                    |
| `test_get_position`                           | Buy then retrieve position, verify `symbol`/`size`/`average_entry_price`.                |
| `test_place_sell_order_sufficient_position`   | Buy enough, sell 5, verify cash increase and position size decrease.                     |
| `test_place_sell_order_insufficient_position` | Buy 5, try to sell more, verify no change, no transaction, and `Event.OrderFailed` fired with status `REJECTED`. |
| `test_portfolio_value`                        | Buy, verify `get_portfolio_value()` returns non-negative float.                          |
| `test_save_load_state`                        | Buy 20, buy 5, save state, re-init `BrokerManager`, verify cash and positions match (ignoring new initial cash/commission). |
| `test_transaction_logging`                    | Buy then sell, verify transaction log has ≥ 2 records with expected keys.                |
| `test_summarize_positions`                    | Buy, call `summarize_positions()` (verify no exception).                                 |
| `test_summarize_transactions`                 | Buy and sell, call `summarize_transactions(duration=None)` and `(duration='month')`.     |
| `test_summarize_positions_no_positions`       | No positions, call `summarize_positions()`, verify output contains "No positions currently held." |
| `test_summarize_transactions_no_history`      | No transactions, call `summarize_transactions()`, verify output contains "Initial State" or "No transactions recorded and no positions held." |
| `test_summarize_transactions_with_pnl_and_duration` | The most complex test. Mocks `datetime` and `get_last_price` to control transaction timestamps. Creates transactions at 60, 15, 5, and 2 days ago, then calls `summarize_transactions(duration='month')`. Verifies output contains the correct period, transaction count (3), buys (2), sells (1), commission ($0.01), and net profit ($186.66). |
| `test_event_callback`                          | Mock event_callback, buy, verify it's called with `Event.OrderFilled` and correct `OrderTracker` data. |

### `testutility/backtest.py` (12 tests)

The only test file using a real `backtrader.Strategy` subclass (`MockStrategy`).

Mock helpers:
- `MockMarket` — generates simple daily OHLCV data (price from 100, +1 per day) and returns a top-product list `['2330', 'DUMMY_STOCK_B']`.
- `MockStrategy(bt.Strategy)` — `NAME = "MockStrategy"`, params `('p1', 1), ('p2', 2)`. Buys 1 share when close > 105, closes when close < 95. Has `reset_status()` and `get_name()`.

| Test                              | Description                                                                          |
|-----------------------------------|--------------------------------------------------------------------------------------|
| `test_initial_configuration`      | Verifies defaults (`init_cash=1000000000`, `commission=0.001`, `slippage_prec=0.001`), tests valid setters, verifies invalid values (negative, wrong type) raise `ValueError`. |
| `test_setup_method`               | Verifies `setup()` creates a `bt.Cerebro` instance, data_list and strategy_list are empty. Tests passing a custom `cerebro`. |
| `test_add_symbol`                 | Mocks `cerebro.adddata`, adds two symbols, verifies `adddata` called twice.          |
| `test_add_data_frame`             | Mocks `cerebro.adddata`, adds two DataFrames.                                        |
| `test_add_history_validation`     | Mocks `cerebro.add_order_history`. Tests valid history, non-iterable input, wrong tuple length, zero size, string size, negative price, string price, empty `data_name`. |
| `test_add_strategy`               | Mocks `cerebro.addstrategy`, adds `MockStrategy`, verifies `strategy_list` and `cached_last_tradding_day`. |
| `test_add_optstrategy`            | Mocks `cerebro.optstrategy`, adds `MockStrategy` with kwargs, verifies parameters.  |
| `test_eval_basic`                 | Mocks `cerebro.run` returning a mock strategy instance with mock analyzer data. Verifies `get_analysis()` returns a result with `strategy`, `profit`, `score`. |
| `test_eval_with_history`          | Add history, run `eval()`, verify `MockStrategy.initial_order_history` is set.       |
| `test_save_report`                | Mocks `cerebro.run`, `cerebro.plot` (returning a nested list of Figure wrappers), `cerebro.broker.getvalue`. Verifies `savefig` called with filename containing `"bt_plot_MockStrategy.png"`. |
| `test_show_result`                | Mocks `cerebro.run` and `cerebro.broker.getvalue`, captures stdout, verifies output contains "Backtest Results Summary", "MockStrategy", "Profit". |
| `test_eval_lock`                  | Replaces `_EVAL_LOCK` with a mock that returns `True` from `locked()`. Verifies `acquire` and `release` called, and `cerebro.run` proceeds. |

### `testutility/integration.py` (4 tests)

End-to-end flow tests with the most extensive mocking (12+ `patch` context managers per test).

| Test                              | Description                                                                                |
|-----------------------------------|--------------------------------------------------------------------------------------------|
| `test_buying_flow`                | End-to-end buy: mocks BrokerManager, Market, MarketTime, AppConfigManager, StrategyManager, Analyzer, datetime. Configures mock data so `2330` is a buy candidate. Verifies `BrokerManager.place_order` called with `symbol='2330'`, `size=1000`, `action=OrderAction.BUY`. |
| `test_selling_flow`               | End-to-end sell: same mocks plus `Recorder`. Mocked `Recorder` returns an open `2330` position with 3 transactions (2 buys, 1 sell). Mocked `StrategyManager` returns a sell signal (`size=4000`). Verifies `BrokerManager.place_order` called with `symbol='2330'`, `size=4000`, `action=OrderAction.SELL`. |
| `test_selling_flow_take_profit`   | Similar to above, with `strategy.default = 'sma_crossover'` and a real `MovingAverageCrossover` strategy mock. Verifies sell size is 2000 (determined by strategy's take-profit logic). |
| `test_selling_flow_stop_lose`     | Similar to take-profit test, but current price is set to 540 (90% of entry 550), triggering stop-loss. Verifies sell size is 4000 (full position). |

## 4. Key Testing Patterns

- **Mocking is pervasive.** Almost every test uses `unittest.mock.patch` to isolate the system under test from the market data providers, broker, and SQLite database.
- **One real DB test.** `test_recorder_save_and_load` is the only test that uses a real SQLite database (via `tempfile`) instead of mocking.
- **Private method access.** Tests reach into private Core methods using Python's name-mangled names (`_Core__sanitycheck`). This is intentional and the tests must be updated when the internal API changes.
- **Sleep mocking.** `sleep_with_flag` and `sleep_until_with_flag` are mocked to return after a short delay, preventing test threads from blocking indefinitely.
- **`MockPosition` helper.** The trading and integration test files define a small `MockPosition` dataclass to avoid pulling in the full `Position` from the broker package.

## 5. Known Limitations

- The test runner has no fixtures or setup/teardown at the group level (each test manages its own state).
- Tests run sequentially. There is no parallel test execution.
- The "all" keyword expands to the full list of test names for that group. There is no test selection by tag or category.
- The custom test framework has no built-in assertion introspection; a test that returns `False` or raises is treated the same as a hard failure, with no diff output.
