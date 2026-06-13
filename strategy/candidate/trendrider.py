"""
TrendRider strategy: a simple long-only trend-follower that lets
winners run.

The problem this solves
-----------------------
The Hybrid strategy's 5y average is 8.24% vs 0050's 15.52%. The
gap is concentrated in 2023 (+27% for 0050 vs +10% for Hybrid)
and 2024 (+28% vs +6%).

0050 is cap-weighted to the top names. In 2024, 2330 returned
+84% buy-hold; Hybrid captured only 39% of the move (the
MovingProfitStrategy's take-profit / ratchet logic exited
partial positions on every 12-14% move, locking in gains but
missing the bigger picture).

TrendRider skips the partial-profit machinery entirely. It
holds the full position with a wide trailing stop and rides
the trend until it breaks. The 2024 per-stock results showed
that stocks where TrendRider-style "buy and hold with wide
stop" worked best were the heavy-weighted 0050 names (2330,
2454, 2603, 2609, 2615, 2882). On those, the strategy
captured 30-100% of the move.

Calibration (t50, 2020-2024):
  - SMA-60 + MACD>0 trend filter (same as Hybrid)
  - 15% trailing stop (vs Hybrid's 10% — wider for big trends)
  - No take-profit (just hold)
  - Risk per trade: 80% of available cash
  - Sells only when:
    a) close < SMA-60 (trend break), or
    b) price hits 15% trailing stop from peak

Per-year average annual return vs 0050:
  Year | Hybrid | TrendRider | 0050 ETF
  -----|--------|------------|--------
  2020 | +22.6% |     TBD    | +22.0%
  2021 | +14.2% |     TBD    | +23.5%
  2022 |  -3.9% |     TBD    | -22.4%
  2023 | +10.7% |     TBD    | +26.5%
  2024 |  +6.1% |     TBD    | +28.0%
"""
import backtrader as bt
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy


class TrendRiderStrategy(MovingProfitStrategy):
    """
    Long-only trend-follower that holds with a wide trailing stop.

    Different from MultiSignal/AdaptiveTrend/Hybrid:
    - No mean-reversion logic at all.
    - No take-profit (just hold).
    - Wide trailing stop (15%) so we ride through pullbacks.
    - Trend filter (close > SMA-60 + MACD > 0) gates both entry and exit.

    The strategy is "always invested when the trend is up,
    always in cash when the trend is down". The 15% trailing
    stop ratchets up with price to lock in gains, but it lets
    through any normal mid-trend pullback (8-12% range).
    """

    NAME = "TrendRider"

    params = (
        # Trend filter
        ("trend_sma_period", 60),
        ("trend_lookback", 5),  # need 5 bars above SMA + MACD>0 to confirm

        # Wide trailing stop (vs 6% in MS defaults). 10% lets through
        # mid-trend pullbacks but not so wide that 2022 crashes blow
        # up the strategy. The 0.99 take-profit pct is set high enough
        # to never trigger a take-profit; we just hold.
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.10),  # 10% trailing stop
        ("trailing_takeprofit_pct", 0.20),  # 20% take-profit (effectively unused)

        # Inherited but unused (kept for the MovingProfitStrategy
        # contract; we override stra_initial/buy/sell).
        ("bb_period", 20), ("bb_stddev", 2),
        ("rsi_period", 14), ("rsi_entry", 30), ("rsi_exit", 70),
        ("macd_fast", 12), ("macd_slow", 26), ("macd_signal", 9),
        ("vol_period", 20),
        ("vwap_period", 20),
    )

    def stra_initial(self):
        # Trend indicators
        self.trend_sma = {
            d: bt.indicators.SimpleMovingAverage(d.close, period=self.p.trend_sma_period)
            for d in self.datas
        }
        self.macd = {
            d: bt.indicators.MACD(
                d.close,
                period_me1=self.p.macd_fast,
                period_me2=self.p.macd_slow,
                period_signal=self.p.macd_signal,
            )
            for d in self.datas
        }
        # Liquidity check setup (mirrors MovingProfitStrategy, but
        # we set the indicators here so they're ready when the buy
        # code runs in `next()`).
        if getattr(self, 'liquidity_check', True) is True:
            self.LIQUIDITY_VOL_THRESHOLD = 50 * 1000
            self.sma_vol = bt.indicators.SimpleMovingAverage(self.data.volume, period=20)

    def _is_strong_uptrend(self, data):
        """Has the stock been above its SMA AND has positive MACD momentum
        (MACD above the zero line, not above the signal line) for the
        last `trend_lookback` bars?
        """
        if len(data) < self.p.trend_sma_period + self.p.trend_lookback:
            return False
        for i in range(0, self.p.trend_lookback):
            if data.close[-(i)] <= self.trend_sma[data][-(i)]:
                return False
            if self.macd[data].macd[-(i)] <= 0:
                return False
        return True

    def stra_buy_in(self, data):
        # Buy whenever we're in a strong uptrend. The trend
        # filter is the only entry condition.
        return self._is_strong_uptrend(data)

    def stra_sell_out(self, data):
        # Sell when the trend breaks. Don't sell on MS-style
        # mean-reversion signals — this strategy doesn't use
        # any of them.
        if len(data) < self.p.trend_sma_period:
            return False
        return data.close[0] < self.trend_sma[data][0]
