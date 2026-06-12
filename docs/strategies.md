# Strategies

The `strategy/` package implements a backtrader-based strategy framework with maturity-level gating, a rich `MovingProfitStrategy` base with trailing stop/take-profit, and a set of candidate + experimental strategies.

## 1. `StrategyManager` (`strategy/strategy.py`)

The central registry for all trading strategies. Contains a nested `Level` enum that controls which strategies are available for production use:

```python
class StrategyManager:
    class Level(Enum):
        OFFICIAL   # production
        BETA       # active but unproven
        TESTING    # only loaded when test > 0
```

### Methods

| Method                                          | Description                                                |
|-------------------------------------------------|------------------------------------------------------------|
| `register_strategy(new_strategy, level)`        | Registers a strategy class under a given level. Raises on duplicate `NAME`. |
| `get_strategy_list(levels=None)`                | Returns strategy classes for the given levels (defaults to `[Level.OFFICIAL]`). |
| `get_strategy_by_name(name)`                    | Looks up a strategy across all levels.                     |
| `get_default_strategy()`                        | Returns the first `OFFICIAL` strategy, falling back to `BETA`. |

The constructor hardcodes the registration of all strategies. Currently only `MovingAverageCrossoverStrategy` is `OFFICIAL`. All others (BreakoutMomentum, RSI, BollingerMeanReversion, MACD/EMA Crossover, VWAP Cross, MultiSignal) are `BETA`. A handful of experimental strategies (MACE, BME, PVS, VWAPStrategy, VolumeSpike) are `TESTING` and only registered when `test > 0`.

## 2. Custom Indicators (`strategy/indicator.py`)

All extend `bt.Indicator`:

| Indicator               | Description                                                                                                |
|-------------------------|------------------------------------------------------------------------------------------------------------|
| `PriceLine`             | Single-line indicator mirroring `data.close`. Trivial.                                                     |
| `OnBalanceVolume`       | OBV. Requires minimum 2 periods. Accumulates volume based on close direction.                              |
| `AccumulationDistribution` | A/D Line. Money Flow Multiplier formula. Guards division by zero when `high == low`.                    |
| `ChaikinMoneyFlow`      | CMF with configurable `period` (default 20). Sum of Money Flow Volume over lookback / total volume.         |
| `VWAP`                  | Volume Weighted Average Price. Uses **`data.turnover`** (not `close * volume`) — depends on `ExtPandasDataFeed`'s `Turnover` column. Configurable `period` (default 20). Overlays price (`plotinfo = dict(subplot=False)`). |

**Surprising detail:** the VWAP indicator uses `data.turnover` rather than computing `close * volume`. This means it depends on `ExtPandasDataFeed` providing a `Turnover` column.

## 3. Base Strategy (`strategy/basic/basicstrategy.py`)

### `BasicStrategy(bt.Strategy)`

Base class for all strategies. Class-level constants: `LOT_UNIT = 1000`, `MIN_CASH_PER_TRADE = 150000`, `NAME = "AdavanceStrategy"` (note: typo preserved).

State per data feed:
- `active_trades` — dict of open positions keyed by data feed, tracking entry date, avg entry price, remaining size, total cost.
- `trading_history` — list of completed trade portions with PnL and win/loss flags.
- `last_trade` — dict tracking the most recent trade.

Methods:
- `get_name()` — generates a parameter-encoded name string.
- `notify_order(order)` — Backtrader order lifecycle handler. On buy: creates/updates `active_trades`. On sell: calculates PnL for the sold portion, records it in `trading_history`, removes fully closed positions. **Warns if PnL < -15%**.
- `notify_trade(trade)` — logs trade open/close/update events.
- `start()` — applies `initial_order_history` to each data feed, setting initial stop/trailing levels.
- `stop()` — prints summary statistics (total trades, win rate, total PnL, open positions).
- `buy(data, size)` / `sell(data, size)` — wraps Backtrader's buy/sell with logging. Sell cancels any pending order first.

### `BasicExitStrategy(BasicStrategy)` (Template Method)

Abstract subclass defining the Template Method pattern. Subclasses must implement:
- `stra_initial()` — set up indicators.
- `stra_buy_in(data)` — return True/False for buy signal.
- `stra_sell_out(data)` — return True/False for sell signal.

## 4. `MovingProfitStrategy` (`strategy/basic/movingprofit.py`)

The most important concrete base strategy. Implements a complete trailing stop-loss / trailing take-profit system with **partial position selling**.

### Key params

| Param                     | Default | Description                                              |
|---------------------------|---------|----------------------------------------------------------|
| `risk_per_trade`          | 0.8     | Fraction of cash to risk per trade.                      |
| `trailing_stop_pct`       | 0.06    | Initial stop at 6% below entry.                          |
| `trailing_takeprofit_pct` | 0.08    | Initial take-profit at 8% above entry.                   |

**Invariant:** `trailing_takeprofit_pct > trailing_stop_pct` (enforced in `__init__`).

### `calc_selling_size(current_size, current_price)`

Divides position into 5 lots. Sells one lot at a time (ensuring minimum cash per trade).

### `next()` — the main loop

For each data feed with a position:
1. **Update trailing stop** when price rises.
2. **Check stop-loss** (triggered by `trailing_stop_pct`).
3. **Check strategy sell-out** (calls `stra_sell_out`).
4. **Check trailing stop** (after price movement).
5. **Check trailing take-profit**: on hit, sells a partial lot and **ratchets both the stop-loss and trailing stop upward** to lock in profit.

On entry:
1. Check liquidity (20-day SMA volume > 50K).
2. Calculate lot size from available cash.
3. Set all four price levels (entry, stop, trailing stop, trailing take-profit).

**Design insight:** the take-profit logic does NOT sell the full position — it sells one calculated lot and then adjusts the stop-loss upward. This is **partial-profit-taking**, not a full exit.

## 5. Candidate Strategies (`strategy/candidate/`)

All extend `MovingProfitStrategy` and inherit the trailing stop/take-profit system.

### `mac.py` — Moving Average Family

| Strategy                          | NAME                      | Level     | Logic                                                        |
|-----------------------------------|---------------------------|-----------|--------------------------------------------------------------|
| `MovingAverageCrossoverStrategy`  | `MovingAverageCrossover`  | OFFICIAL  | SMA(10) crosses above SMA(20) → buy; below → sell.           |
| `EMACrossoverStrategy`            | `EMACrossover`            | BETA      | Same logic with EMA instead of SMA.                          |
| `MACDCrossoverStrategy`           | `MACDCrossover`           | BETA      | MACD(10, 20, 10) line crosses above signal → buy; below → sell. |

### `rsi.py` — RSI Family

| Strategy                      | NAME                      | Level     | Logic                                              |
|-------------------------------|---------------------------|-----------|----------------------------------------------------|
| `RelativeStrengthIndexStrategy` | `RelativeStrengthIndex` | BETA      | RSI(10). Buy when RSI < 35 (oversold); sell when RSI > 65 (overbought). |
| `RSI_SMA`                     | `RSI_SMA`                 | (unregistered) | Same thresholds, but uses `RSI_SMA` indicator variant. |

### `bm.py` — Breakout Momentum

- `BreakoutMomentumStrategy` (`NAME="BreakoutMomentum"`, `BETA`) — uses `Highest` over 15 periods. Buys when close breaks above the highest high of the lookback window. `stra_sell_out` always returns `False` — exits are purely via the trailing stop/take-profit. Also checks 20-day SMA volume > 100 as a liquidity filter.

### `bmr.py` — Bollinger Mean Reversion

- `BollingerMeanReversionStrategy` (`NAME="BollingerMeanReversion"`, `BETA`) — uses Bollinger Bands(20, 2). Buys when close touches or goes below the lower band. Sells when close returns to the middle band. Classic mean-reversion.

### `multisignal.py` — Multi-Signal

- `MultiSignalStrategy` (`NAME="MultiSignal"`, `BETA`) — the most complex candidate strategy. Combines four signal sources:
  - **Bollinger Bands** (20, 2): buy if price was below lower band in last 20 days and is now above it.
  - **RSI** (14): buy if RSI was below 30 in last 20 days and is now above 30.
  - **MACD** (12, 26, 9): buy if MACD was below signal in last 20 days and is now above.
  - **VWAP** (short=1, long=20): buy when short VWAP > long VWAP.

  The `stra_buy_in` method currently requires ALL of: BB buy signal AND RSI buy signal (VWAP and MACD are commented out). The `stra_sell_out` requires EITHER BB sell OR RSI sell signal.

  **Non-standard detail:** VWAP short period is 1 (single-day VWAP), which effectively compares today's VWAP against a 20-day VWAP.

## 6. Experimental Strategies (`strategy/experiment/`)

### `bollinger.py` — `BollingerRebound`

- Extends `BasicStrategy` (not `MovingProfitStrategy`). Buys when `close < lower band`. Sells when `close > upper band` (not middle band, despite the docstring saying "middle band"). Uses `print()` for logging rather than `dbg_*` system. **Unregistered in `StrategyManager`.**

### `vwap.py` — Three VWAP variants

- `VWAPStrategy_Legacy(BasicStrategy)` (`NAME="VWAPS"`, unregistered) — simple VWAP(20) crossover. Buy when close > VWAP, sell when close < VWAP. Uses 10% of cash per trade.
- `VolumeWeightedAveragePriceStrategy(MovingProfitStrategy)` (`NAME="VolumeWeightedAveragePrice"`, unregistered) — same logic but with trailing stop/take-profit.
- `VolumeWeightedAveragePriceCrossStrategy(MovingProfitStrategy)` (`NAME="VolumeWeightedAveragePriceCross"`, `BETA`) — uses SMA(10) and SMA(20) **despite the name suggesting VWAP**. The `stra_initial` method is defined twice — the second definition overwrites the first, so it actually uses SMA, not VWAP. **This appears to be a bug.**

### `volumn.py` (sic) — Six Volume-Based Strategies

All extend `BasicStrategy` (no trailing stop/take-profit). All use 10% of cash per trade.

| Strategy                       | NAME    | Level   | Logic                                                                  |
|--------------------------------|---------|---------|------------------------------------------------------------------------|
| `PriceVolumeStrategy`          | `PVS`   | TESTING | SMA(5) vs SMA(20) crossover with volume confirmation (close > open + volume increasing). |
| `OBVStrategy`                  | `OBVS`  | (unreg) | On-Balance Volume crossover with price.                                |
| `ADLineStrategy`               | `ADLS`  | (unreg) | Accumulation/Distribution line crossover with price.                   |
| `PriceVolumeBreakoutStrategy`  | `PVBS`  | (unreg) | Breakout from 20-day high/low with 1.5x volume threshold.               |
| `CMFStrategy`                  | `CMFS`  | (unreg) | Chaikin Money Flow > 0 buys, < 0 sells.                                |
| `VolumeSpikeStrategy`          | `VSS`   | TESTING | Volume spike (2x SMA) with price direction confirmation.              |

### `experiment.py` — Test Variants

Contains `Test2Strategy(MovingProfitStrategy)` and `TestStrategy_back(BasicStrategy)`. Both are experimental multi-signal strategies combining BB, RSI, MACD, and volume. Neither is registered.

### `test.py` — Legacy Strategies

- `MovingAverageCrossover` (`NAME="MAC"`) — simple SMA crossover with fixed 5% stop-loss and 20% take-profit.
- `MovingAverageCrossoverEn` (`NAME="MACE"`, `TESTING`) — enhanced version with trailing stop/take-profit.
- `BreakoutMomentum` (`NAME="BM"`) — **defined twice** in the same file; the second definition silently replaces the first. Breakout from 20-day high with 3% stop and 15% take-profit.
- `BreakoutMomentumEn` (`NAME="BME"`, `TESTING`) — enhanced breakout with trailing stop/take-profit.

## 7. How Strategies Are Loaded

```python
from strategy.strategy import StrategyManager

# Default: load OFFICIAL strategies only
strategies = StrategyManager.get_strategy_list()  # [MovingAverageCrossoverStrategy]

# BETA strategies
strategies = StrategyManager.get_strategy_list(levels=[StrategyManager.Level.OFFICIAL, StrategyManager.Level.BETA])

# All including TESTING (requires test > 0 flag — see `test = True` argument to StrategyManager)
strategies = StrategyManager.get_strategy_list(levels=list(StrategyManager.Level))
```

The default strategy is fetched via `StrategyManager.get_default_strategy()` — first `OFFICIAL`, fallback to `BETA`.

## 8. Strategy Parameter Encoding

`BasicStrategy.get_name()` generates a parameter-encoded name string by appending abbreviated param values. This is used by:
- `Backtest` to identify strategies in result reports.
- `Evaluate` to record which strategy matched a buy candidate (so the same strategy is reused for sell evaluation).
- `Recorder` to tag transactions with the originating strategy.
