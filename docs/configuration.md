# Configuration & Paths

TradeBot uses a class-based configuration system (not dictionaries or `TypedDict`). The schema is defined as nested Python classes, and `ConfigManager` introspects class attributes to serialize/deserialize to JSON.

## 1. The Config Schema: `AppConfig`

Defined in `core/config.py`. The schema has four nested classes:

```python
class AppConfig(BasicConfig):
    class about:
        program_name = "TradeBot"
        version = "0.0.1"

    class debug:
        development = False

    class path:
        root = "~/.config/investment"
        config = "config.json"
        data = "data"          # market data cache
        log = "log"            # debug logs
        key = "key"            # API keys (FinMind token, etc.)
        broker = "broker"      # broker-specific state (positions, transactions, trades)
        simulate = "simulate"  # simulation runs (one subdir per run)
        trade_cmd_history = "cmd_history"
        backtest = "backtest"
        bt_report = "bt_report"  # backtest reports

    class stock:
        lot_unit = 1
        cash_min_per_trade = 1000
        cash_max_per_trade = 10000
```

The base class `BasicConfig` (in `utility/config.py`) provides default `about` and `path` nested classes.

## 2. `AppConfigManager`

`AppConfigManager` extends `ConfigManager` and overrides the root path to `~/.config/investment`. It provides dot-notation access to config values.

### Methods

| Method                     | Description                                                                 |
|----------------------------|-----------------------------------------------------------------------------|
| `get(key)`                 | Dot-notation read: `cm.get("about.version")` → `"0.0.1"`.                  |
| `set(key, value, save=True)` | Dot-notation write. Persists to JSON by default.                          |
| `get_path(key)`            | Joins with `path.root` and expands `~`. Returns absolute paths unchanged.   |
| `load(config_file)`        | Loads JSON and hydrates the config object via `_loadDict()`.                |
| `save()`                   | Writes `{path.root}/{path.config}` as JSON, creating directories.            |
| `toDict()` / `toJson()`    | Serialization helpers.                                                       |
| `dump()`                   | Pretty-prints current config.                                                |

### Example

```python
cm = AppConfigManager()
cm.load(cm.get_path('config'))          # load ~/.config/investment/config.json

cm.get('about.version')                  # '0.0.1'
cm.set('path.root', '/custom/path')     # persists to JSON
cm.get_path('data')                      # '/custom/path/data' (absolute, expanded)

cm.set('stock.cash_max_per_trade', 50000)  # used by OrderChecker
```

## 3. Config File Location

Default: `~/.config/investment/config.json`.

Override at startup by setting `path.root` before calling `load()`.

## 4. Mode-Specific Path Rewrites

The mode flag in `investor.py` rewrites `path.broker` **before** starting the CLI. This is the canonical mode switch — `path.broker` controls where broker state, trade DB, and transaction log live.

| Flag / Mode                    | `path.broker` value                | Notes                          |
|--------------------------------|------------------------------------|--------------------------------|
| `-d` (development)             | `broker_development`               | All dev work                   |
| `-m test`                      | `broker_test`                      | Test suite                     |
| `-m backtest`                  | `broker_development`               | Reuses dev broker state        |
| `-m simulate`                  | `simulate/<timestamp>`             | Per-run directory              |
| default (real trade)           | `broker_<git_branch>`              | Falls back to `broker_<args.broker_type>` outside git repo |
| `--broker shioaji`             | `broker_<branch>` or `broker_shioaji` | Same as above                 |

`path.broker` is interpreted relative to `path.root` by `get_path('broker')`. So in development, all state lives under `~/.config/investment/broker_development/`.

## 5. Paths Set From Config

Several subsystems read path values at startup:

| Subsystem                  | Path key          | Used for                                       |
|----------------------------|-------------------|------------------------------------------------|
| `DebugSetting.setDbgPath`  | `path.log`        | Daily log folder: `{path.log}/<YYYYMMDD>/`     |
| `Market.CACHED_DATA_PATH`  | `path.data`       | Provider CSVs: `{path.data}/{provider}/datas/` |
| `Recorder.__init__`        | `path.broker`     | SQLite: `{path.broker}/trade.db`               |
| `MockBroker` state         | `path.broker`     | JSON: `{path.broker}/positions.json`           |
| `TransactionManager`       | `path.broker`     | CSV: `{path.broker}/transaction.csv`           |
| `Backtest`                 | `path.bt_report`  | PNG plots + CSVs                               |
| `Simulate`                 | `path.broker`     | Per-run JSON state under `simulate/<ts>/`      |
| `ShioajiBroker`            | `path.key`        | `.env` file with API credentials               |

## 6. The `debug.development` Flag

Set to `True` for any non-real-trade mode (`-d`, `-m test`, `-m backtest`, `-m simulate`). When `False`, the CLI prints a confirmation prompt before starting live trading.

Used by:
- `DebugSetting` (controls log verbosity).
- `CommandLineInterface.help` (hides internal commands when not in development).
- `Simulate` (controls data update behavior).

## 7. Schema vs Runtime Mutation

The `AppConfig` class defines **defaults** that ship with the code. Runtime overrides (e.g., increasing `cash_max_per_trade` for a particular account) are persisted to `config.json` and override the class defaults on next load.

This is the "class-based config" pattern: schema is code, values are JSON.
