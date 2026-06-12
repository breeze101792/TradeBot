# Market Data

The `market/` package wraps multiple Taiwan-stock data providers behind a unified `Market` facade. It also manages market timing (open/close/update times, non-trading days).

## 1. `Market` (`market/market.py`)

The top-level facade. Holds a hardcoded list of provider classes `[FindMind, TWSE, Yahoo]` and switches between them via `switch_market(market_name)`. The currently active provider is stored in `self.instance`.

### Static helper: `MarketTime`

Attached as `self.time`. Manages market-schedule logic:

| Class attribute        | Type | Default | Description                                |
|------------------------|------|---------|--------------------------------------------|
| `NON_TRADING_DAYS`     | set  | empty   | Set of dates the market was unexpectedly closed. |
| `MARKET_OPEN_TIME`     | time | 09:00   | Market open.                               |
| `MARKET_CLOSE_TIME`    | time | 13:30   | Market close.                              |
| `MARKET_UPDATE_TIME`   | time | 18:00   | End-of-day data finalization.              |

Static methods:
- `get_next_market_update_time(now=None)` — next 18:00 (or today if before 18:00 and not weekend).
- `get_next_market_close_time(now=None)` — next 13:30 weekday.
- `get_next_market_open_time(now=None)` — next 09:00 weekday.
- `get_previous_market_update_time(now=None)` — most recent 18:00 weekday.
- `is_trading_day(date)` — weekday and not in `NON_TRADING_DAYS`.

The methods iterate backward/forward through calendar days, skipping weekends and non-trading days. `NON_TRADING_DAYS` is maintained with a ±7-day window of the current date to keep the set small.

### Methods

| Method                                          | Description                                                                              |
|-------------------------------------------------|------------------------------------------------------------------------------------------|
| `switch_market(market_name)`                    | Rebinds `self.instance` to the named provider class.                                    |
| `get_data(product_id, start_date, end_date, force_update=False)` | Delegates to provider's `get_data()`. Caps `end_date` to the previous market update. |
| `get_data_list(market, country, product_type)`  | Fetches and caches the full product listing in `cached_stock_info_frame`.               |
| `get_data_info(product_id)`                     | Returns a dict (code, type, name, start, market, category, country) from cached frame.   |
| `get_top_product_list(number=50)`               | Returns a hardcoded list of 52 top Taiwan-stock tickers (capped at 50).                  |
| `update_data(product_list, force_update, update_trading_day)` | Delegates to provider. If the provider returns a `date` (non-trading day), records it via `MarketTime.add_non_trading_day`. |
| `get_markget_list()`                            | **Typo preserved from source.** Returns the available provider names.                   |

## 2. `DataProvider` (`market/dataprovider.py`)

The abstract base class for all providers (not formally abstract, but subclasses must implement `download_data` and optionally `download_data_list`).

### Class-level constants

| Name                       | Default       | Notes                                                       |
|----------------------------|---------------|-------------------------------------------------------------|
| `NAME`                     | `'provider'`  | Subclass overrides with `'twse'` / `'findmind'` / `'yahoo'`. |
| `CACHED_DATA_PATH`         | `'./.data'`   | Set at startup to `path.data` from config.                  |
| `SUPPORTED_ADJUSTED_DATA`  | `False`       | `FindMind` overrides to `True` (date-stamped cache).        |
| `MARKET_OPEN_TIME` / `CLOSE_TIME` / `UPDATE_TIME` | `None` | Some providers override with their market hours.            |

### `get_data(product_id, start_date, end_date, incremental_update=True, force_update=False, update=False) -> DataFrame`

A sophisticated caching layer (~180 lines). On each call:

1. Computes the cache file path: `{CACHED_DATA_PATH}/{NAME}/datas/{product_id}.csv` (or `.../datas/{YYYYMMDD}/{product_id}.csv` if `SUPPORTED_ADJUSTED_DATA`).
2. Loads the cached CSV if present.
3. Decides whether to download based on `force_update`, cache emptiness, or `incremental_update` logic (comparing cached max date against the requested/expected end date).
4. Calls `self.download_data()` to fetch new data.
5. Merges old and new data, deduplicates, sorts, and saves back to CSV.
6. Returns a DataFrame indexed by `Date` with columns: `Open`, `High`, `Low`, `Close`, `Volume`, `Turnover`, `Change`, `Transaction`.

### `get_data_list(market, country, force_update=False, product_type='STOCK')`

Caches the product listing as `{CACHED_DATA_PATH}/{NAME}/lists/data_list_{market}_{country}_{type}_{YYYYMMDD}.csv`. Falls back to stale cache if download fails (so a transient provider error doesn't lose the listing).

### `update_data(product_list=None)`

Iterates through products (or all from `get_data_list()`), downloads incrementally. Uses a file-based lock (`update.lck`) to prevent concurrent update runs. Returns:
- `True` on success.
- A `date` object if all updates failed (signaling a non-trading day, which the caller can record).
- `False` on other failure modes.

### `wait_quota(require_quota)`

Polls `get_quota()` and sleeps 10 minutes if below the threshold. Used by FinMind which has API call limits.

### `get_last_trading_update_date()`

Returns the most recent weekday before the current time (or yesterday if before `MARKET_UPDATE_TIME`).

### Static helpers

- `save_to_csv(df, filepath)` — saves with folder creation.
- `load_from_csv(filepath)` — loads with `Date` index.

## 3. Providers

### `TWSE` (`market/provider/twse.py`)

Uses the `twstock` library.

**Key characteristics:**
- `NAME='twse'`, `SUPPORTED_ADJUSTED_DATA=False`.
- **Rate limiting** via a `FileLock` and `API_CALL_INTERVAL_SECONDS = 1.6`. The `lock()`/`unlock()` methods enforce a minimum 1.6-second gap between API calls.
- **Realtime price** support: the only provider with `get_current_price(symbol, price_type)`.

**Methods:**

- `download_data_list(market, country, product_type)` — iterates `twstock.codes`, filters for `type='股票'` (stock) and `market='上市'` (listed). Returns DataFrame with `code/type/name/start/market/category/country`.

- `download_data(product_id, start_date, end_date)` — uses `twstock.Stock.fetch_from(year, month)` to iterate historical monthly data. Validates every row (no `None` fields, positive prices, non-negative volume). Returns DataFrame with the standard OHLCV + Turnover/Change/Transaction columns. Data goes back to year 2000 by default.

- `convert_market(market_str)` — maps Chinese names: `"上市"` → `"listed"`, `"上櫃"` → `"otc"`, `"興櫃"` → `"emerging"`.

- `get_current_price(symbol, price_type)` — calls `twstock.realtime.get()` and returns bid (`BID`), ask (`ASK`), or latest-trade (`LAST`) price. Defaults to bid if trade is `'-'`. Uses the `FileLock` for thread safety.

### `FindMind` (`market/provider/findmind.py`)

Uses the `FinMind` API for Taiwan market data. **Marked experimental** in source comments: "don't use it, since it's not all verified with other trusted data."

**Key characteristics:**
- `NAME='findmind'`, `SUPPORTED_ADJUSTED_DATA=True` (the only provider with this flag; uses date-stamped cache folders).
- Loads an API token from `~/.findmind.key` via `_load_token()`.
- `__init__` swaps `self.download_data` to point to `self.fetch_adjusted_data_api` (not the parent's `download_data`), so all data fetches go through the adjusted-data path.

**Methods:**

- `get_quota()` — queries the FinMind API for remaining quota, keeping a 100-call safety buffer.
- `download_data_list(...)` — fetches `taiwan_stock_info` and `taiwan_stock_delisting`, filters out delisted stocks, duplicates, indexes, ETNs, and non-digit stock IDs. Defaults to `'listed'` market.
- `fetch_data(ticker, start_date, end_date)` — raw (unadjusted) daily data via `taiwan_stock_price`. Renames columns and adds a zeroed `Transaction` column.
- `fetch_adjusted_data_api(ticker, ...)` — fetches from the `TaiwanStockPriceAdj` FinMind endpoint. Recalculates the `Change` column from adjusted closes.
- `fetch_adjusted_data(ticker, ...)` — **the crown jewel: a ~280-line manual OHLC adjustment engine** that processes dividends and capital reductions. Fetches raw prices, fetches dividend announcements (cash `息`/`除息`, stock `權`/`除權`, combined `除權息`), fetches capital reduction reference prices, then iterates all events in reverse chronological order, applying multiplicative adjustment factors backward in time to OHLC prices and volume. Capital reduction events adjust both price and volume by the ratio `after_price / before_price`. Recalculates `Change` at the end.
- Also exposes `fetch_dividend_result()`, `fetch_market_value()`, `fetch_capital_reduction_data()` for one-off data fetches.

### `Yahoo` (`market/provider/yahoo.py`)

The simplest provider. Uses `yfinance` with `.TW` suffix (e.g., `2330.TW`).

**Key characteristics:**
- `NAME='yahoo'`, `SUPPORTED_ADJUSTED_DATA=False`.
- `download_data(product_id, start_date, end_date)` — calls `yf.Ticker(yf_code).history(...)` with `period="max"` if no dates given.
- **Does not override `download_data_list()`** — inherits the unimplemented version from `DataProvider` which raises an error. Yahoo cannot enumerate products.

## 4. Product Types (`market/product/constant.py`)

Minimal enum:

```python
class ProductType(Enum):
    STOCK = "STOCK"
    ETF = "ETF"
    ALL = "ALL"
```

## 5. Cache Layout

All providers cache data under `{CACHED_DATA_PATH}/{NAME}/`:

```
.data/
  twse/
    datas/
      2330.csv           # OHLCV + Turnover + Change + Transaction
      2454.csv
    lists/
      data_list_listed_TW_STOCK_20250612.csv
  findmind/
    datas/               # if SUPPORTED_ADJUSTED_DATA
      20250610/          # date-stamped
        2330.csv
      20250611/
        2330.csv
    lists/
      data_list_listed_TW_STOCK_20250612.csv
  update.lck             # file lock for update_data() concurrency
```

## 6. Usage Example

```python
from market.market import Market

market = Market()
# market.switch_market('twse')  # default is first in the list

# Get historical data
df = market.get_data('2330', start_date='2024-01-01', end_date='2024-12-31')
print(df.head())

# Get product info
info = market.get_data_info('2330')
# {'code': '2330', 'type': 'STOCK', 'name': '台積電', 'start': '...', 'market': 'listed', ...}

# Force a full update
market.update_data(['2330', '2454'], force_update=True, update_trading_day=True)
```
