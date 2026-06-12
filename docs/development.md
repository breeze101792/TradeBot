# Development Guide

This document covers logging, conventions, common extension points, and known issues for TradeBot contributors.

## 1. The Custom Logger (`utility/debug.py`)

TradeBot uses a custom bitmask-based logger instead of Python's standard `logging` module.

### Log levels

```python
class DebugLevel:
    DISABLE      = 0x00
    CRITICAL     = 0x01
    ERROR        = 0x02
    WARNING      = 0x04
    INFORMATION  = 0x08
    DEBUG        = 0x10
    TRACE        = 0x20
    LOG          = 0x40
    MAX          = 0xff
```

### Usage

```python
from utility.debug import dbg_trace, dbg_debug, dbg_info, dbg_warning, dbg_error, dbg_critical, dbg_log

dbg_info("starting service")                # writes to debug.log
dbg_warning("reconnecting broker")
dbg_error(f"failed to place order: {e}")
dbg_critical("data corruption detected")
dbg_trace("function call detail")
dbg_log("user-facing journal entry")        # writes to journal.log, not debug.log
```

`dbg_info` uses `\r` prefix for in-place progress updates (e.g., during batch data downloads).

### Log file layout

```
{path.log}/
  20250610/
    debug.log
    journal.log
  20250611/
    debug.log
    journal.log
```

Each log line includes: timestamp, PID, TID (last 3 digits), source file, function, line number, and the message.

### Configuration

```python
from utility.debug import DebugSetting

# Set the log directory (called by investor.py at startup)
DebugSetting.setDbgPath("/path/to/logs")

# Set verbosity
DebugSetting.setDbgLevel("all")               # everything
DebugSetting.setDbgLevel("default")           # CRITICAL+ERROR+WARNING+INFORMATION
DebugSetting.setDbgLevel("development")       # includes DEBUG
DebugSetting.setDbgLevel("CRITICAL")           # only CRITICAL
```

## 2. Config Access

Always go through `AppConfigManager`:

```python
from core.config import AppConfigManager

cm = AppConfigManager()
cm.load(cm.get_path('config'))

cm.get('about.version')
cm.set('stock.cash_max_per_trade', 50000)
cm.get_path('broker')  # /abs/path/to/broker (joined with path.root, expanded)
```

## 3. Interruptible Sleeps

Any sleep that blocks a service thread **must** use `sleep_with_flag` or `sleep_until_with_flag` so the `stop_event` can break it:

```python
from utility.utils import sleep_with_flag, sleep_until_with_flag

# Sleep for N seconds, interruptible
remaining = sleep_with_flag(timeout=10, flag=self.stop_event)
if remaining == -1:
    return  # interrupted

# Sleep until a specific time, interruptible
remaining = sleep_until_with_flag(target_time=next_wakeup, flag=self.stop_event)
```

The functions return `-1` if the flag was set (interrupted), or the remaining time on normal completion.

## 4. Broker Initialization

`BrokerManager.initialize(broker_type=...)` **must be called before**:
- Constructing `Trading`.
- Constructing `Simulate`.
- Constructing any `BrokerManager()` instance.
- Using `MockBroker` or `ShioajiBroker` directly.

Both `Core.initialize()` and `Simulate.__init__` handle this. For new code paths, ensure the same invariant is preserved.

## 5. Strategy Selection

```python
from strategy.strategy import StrategyManager

# Production: only OFFICIAL
strategies = StrategyManager.get_strategy_list()  # defaults to [Level.OFFICIAL]

# BETA experiments
strategies = StrategyManager.get_strategy_list(levels=[StrategyManager.Level.OFFICIAL, StrategyManager.Level.BETA])

# Including TESTING (only when the test flag is on)
strategies = StrategyManager.get_strategy_list(levels=list(StrategyManager.Level))
```

`MovingAverageCrossoverStrategy` is the only `OFFICIAL` strategy at the time of writing.

## 6. Adding a New Strategy

1. Create the strategy class in `strategy/candidate/` (extending `MovingProfitStrategy` for trailing stop/take-profit) or `strategy/experiment/` (extending `BasicStrategy` for simpler behavior).
2. Set a unique `NAME` class attribute.
3. Implement `stra_initial()`, `stra_buy_in(data)`, and `stra_sell_out(data)`.
4. Register it in `StrategyManager.__init__` under the appropriate `Level`.
5. Run backtests to validate (`backtest> strategy set YourName` then `evaluate`).
6. Add a test in `testutility/trading.py` or `testutility/integration.py`.

## 7. Adding a New Market Provider

1. Create a new class in `market/provider/` extending `DataProvider`.
2. Set `NAME` to the provider identifier.
3. Implement `download_data(product_id, start_date, end_date)`.
4. Optionally implement `download_data_list(market, country, product_type)`.
5. Add the class to the `Market` providers list in `market/market.py`.
6. Implement `get_current_price` if realtime price is needed (only `TWSE` currently does this).

## 8. Adding a New CLI Command

1. In the relevant `commands.py` file, define `cmd_xxx(args)` and add a `register_xxx_commands(cli_instance)` function.
2. In `regist_cmd`, use the signature: `regist_cmd(keyword, function_pointer, description, arg_list, group)`.
3. Call the registration function from the appropriate `__init__` (e.g., `TDCLI.__init__` for live trading).

## 9. Thread Safety Considerations

- `BrokerManager` uses a class-level `threading.Lock` — all instance methods are safe to call from multiple threads.
- `OrderService` runs in its own thread; it polls every 1 second.
- `Core`'s 5 services share `self.stop_event` and `trading_status`. The status namespace is **not** thread-safe; concurrent reads may observe partial state, but in practice the trading service finishes writing before the CLI reads.
- `uDatabase` (the SQLite base class) uses a **class-level** lock, so only one DB operation runs across all instances simultaneously.
- For per-`Backtest` thread safety, `_EVAL_LOCK` is held during `eval()`. Different `Backtest` instances can run concurrently.

## 10. Known Issues (from README)

### FIXME items

1. **Hang when `market.get_data` with non-existent symbol.** The TWSE provider does not handle the case where a symbol does not exist gracefully; `fetch_from` may hang.
2. **Insufficient money causes add history to fail.** When cash is too low to fill a backtest order, the order history is not added.
3. **Missing thread lock on backtest.** Some backtest paths lack the `_EVAL_LOCK` guard.
4. **Thread safety on strategy.** Strategies share state across data feeds and are not reentrancy-safe.
5. **Strategy test of last day trade.** No test for the "what happens on the last day of the backtest" case.
6. **Broker submodule test for different provider.** No tests for alternative broker implementations (only `MockBroker` is tested).
7. **Refactor broker for more general APIs.** The current `BaseBroker` interface is tightly coupled to specific use cases.
8. **Test code for core module.** Only partial coverage exists.
9. **Avoid small amount of selling.** Tiny partial sells generate noise and fees.
10. **Skip date crash.** When a date is skipped (market unexpectedly closed), the update system crashes because `update_data` requires every `get_data` to succeed.
11. **Check buy/sell within min/max value of config.** No enforcement that orders fall within `cash_min_per_trade` and `cash_max_per_trade`.
12. **Price error handling on buy/sell.** No robust handling for "could not get real price" cases.
13. **Easy-to-sell stock filter on buy.** No filter for liquidity or sellability when buying.
14. **Separate SVC from broker manager.** Broker service should not be coupled to broker connection.
15. **Reconnect on broker offline.** Limited automatic reconnection logic.
16. **List failed sells.** The `positions` command does not show failed sell evaluations.

### Potential Risk items

1. **`trading/traderecord.py` size inconsistencies.** After manual broker interventions (e.g., user adjusts a position outside the bot), the recorder's view of position size can drift from the broker's actual size. There's no reconciliation logic.
2. **Dynamic load_record to avoid out-of-memory.** The current `Recorder.get_open_trades` loads all open trades into memory; for large portfolios this could exhaust memory.

### TODO items

1. **Real-time profit check on strategy.** Strategies should report unrealized P&L in real time, not just at sell.
2. **History feed-back on trading evaluation (sell/buy).** Past trade outcomes should inform future buy/sell decisions.

## 11. Additional Bugs Noted in Code

These are bugs visible from a code read (not in the README's FIXME list):

1. **`investor.py:134`** — The condition `if args.broker_type != 'mcok'` (typo: `mcok` instead of `mock`) is dead code. The warning branch is always taken for real trading, and the info branch is never taken. **Live trade always enters the warning branch.**
2. **`trading/tradecli.py:45-46, 52-53`** — Operator-precedence bug in `print` statements: `"buying " + "enable" if ... else 'disable'` always prints `"buying enable"` (string concatenation binds tighter than the ternary).
3. **`strategy/strategy.py`** — `VolumeWeightedAveragePriceCrossStrategy.stra_initial` is defined twice; the second (SMA-based) silently replaces the first (VWAP-based).
4. **`strategy/experiment/test.py`** — `BreakoutMomentum` is defined twice in the same file; the second replaces the first.
5. **`utility/parallelprocessor.py`** — Both `ParallelProcessorManager` and `ParallelProcessorQueue` reference `ParallelProcessor._process_chunk` (the Manager's static method) instead of their own. Only the Manager's version is ever used.
6. **`core/database.py`** — `Core.initialize()` has the database initialization **commented out**, so the `Database` class is essentially unused at runtime.
7. **`strategy/strategy.py`** — `MultiSignalStrategy.stra_buy_in` only requires BB + RSI buy signals; VWAP and MACD checks are commented out despite the strategy's name suggesting all four.
8. **`broker/brokers/shioaji/shioajibroker.py:576-580`** — Dead-code `return None` after `dbg_error` and before the actual order placement logic. Any non-BUY/SELL action returns `None` early.
9. **`trading/traderecord.py`** — `show_records` duration filter only shows trades with transactions in the window, but always includes all open trades regardless of duration (a subtle inconsistency).
10. **`market/market.py`** — `get_markget_list()` (typo `markget` instead of `market`) is preserved as-is for compatibility with tests that reference the typo.

## 12. Extension Points

| Want to add...                  | Edit / Create                                                       |
|---------------------------------|---------------------------------------------------------------------|
| New strategy                    | `strategy/candidate/your_strategy.py`, register in `strategy/strategy.py` |
| New market provider             | `market/provider/your_provider.py`, add to list in `market/market.py` |
| New broker implementation       | `broker/brokers/your_broker/`, extend `BaseBroker`                  |
| New CLI command (live)          | `trading/commands.py` or new module, register in `trading/tradecli.py` |
| New CLI command (backtest)      | `backtest/commands.py` or `backtest/btcli.py`                       |
| New CLI command (simulate)      | `simulate/simulatecli.py`                                           |
| New web route                   | Add to `stockwatch/server.py:_register_routes()` and create template |
| New test suite                  | `testutility/your_suite.py`, register in `testutility/testcli.py`   |
| New config key                  | Add to `core/config.py:AppConfig`                                   |
| New log level                   | Add to `utility/debug.py:DebugLevel`                                |

## 13. Development Workflow

### Local setup

```bash
git clone <repo>
cd tradebot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Comment in `python-dotenv` in `requirements.txt` if you need `.env` support for Shioaji credentials.

### Running tests during development

```bash
python investor.py -t
test> broker
test> trading
test> integration
test> backtest
test> test
```

### Running a backtest

```bash
python investor.py -b
backtest> data t5
backtest> strategy set MovingAverageCrossover
backtest> date d1
backtest> evaluate
backtest> report show analysis
```

### Running the simulator

```bash
python investor.py -s
SIM> date 2024-01-01 2024-12-31
SIM> product t5
SIM> start
```

### Debug log level

```python
# in investor.py, uncomment to enable all debug output
DebugSetting.setDbgLevel('all')
```

## 14. File Locations Reference

| Purpose               | Default location                                                |
|-----------------------|-----------------------------------------------------------------|
| Config JSON           | `~/.config/investment/config.json`                              |
| Market data cache     | `~/.config/investment/data/{provider}/datas/`                   |
| Product lists         | `~/.config/investment/data/{provider}/lists/`                   |
| Broker state (JSON)   | `~/.config/investment/broker_<branch>/positions.json`           |
| Trade DB (SQLite)     | `~/.config/investment/broker_<branch>/trade.db`                 |
| Transaction log (CSV) | `~/.config/investment/broker_<branch>/transaction.csv`          |
| Backtest reports      | `~/.config/investment/bt_report/`                               |
| Simulation state      | `~/.config/investment/simulate/<timestamp>/`                    |
| Debug logs            | `~/.config/investment/log/<YYYYMMDD>/`                         |
| FinMind API key       | `~/.findmind.key`                                               |
| Shioaji credentials   | `<path.key>/.env`                                               |
