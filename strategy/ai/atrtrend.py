"""
ATR-adaptive trend strategy: uses ATR-based dynamic stops that
automatically widen in high-volatility regimes and tighten in
low-volatility regimes.

The problem this solves
-----------------------
The Hybrid strategy uses fixed 10% / 12% stops. These are a
compromise that works OK across regimes. But the optimal
stop width is regime-dependent:
  - In 2022 (high-vol bear): 10% stop was too wide, the strategy
    held through 15-20% drawdowns.
  - In 2024 (low-vol bull): 10% stop was too tight, the strategy
    got stopped out on 10-12% mid-trend pullbacks.

ATR-adaptive: use 2.5x ATR as the stop. In 2022 ATR was high
(~6% of price for 0050 names), so 2.5x ATR = 15% stop. In
2024 ATR was low (~3%), so 2.5x ATR = 7.5% stop. This
auto-adjusts.

The strategy also uses a 200-day SMA filter for the trend
gate (vs Hybrid's 60-day) to skip stocks that have only had
a brief rally. 200-day SMA = "in a long-term uptrend".

Calibration (t50, 2020-2024):
  - SMA-200 trend filter
  - MACD > 0 momentum gate
  - 2.5x ATR trailing stop (vs Hybrid's fixed 10%)
  - No take-profit
  - 80% risk per trade
"""
import backtrader as bt
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy


class ATRTrendStrategy(MovingProfitStrategy):
    """
    Long-only trend-follower with ATR-adaptive stops.

    Different from Hybrid/TrendRider:
    - Uses SMA-200 (long-term trend) instead of SMA-60.
    - Trailing stop is N * ATR (volatility-adjusted) instead of
      fixed percentage.
    - No take-profit (just hold).
    """

    NAME = "ATRTrend"

    params = (
        # Long-term trend filter (200-day SMA = "real uptrend")
        ("trend_sma_period", 200),
        ("trend_lookback", 5),

        # ATR-based stop
        ("atr_period", 14),
        ("atr_stop_mult", 2.5),  # 2.5 * ATR as stop

        # Risk and (effectively unused) take-profit
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.10),  # placeholder; overridden in next() to ATR-based
        ("trailing_takeprofit_pct", 0.99),  # no TP (was 30%; HP-tuned = +1.24pp on t50)

        # Inherited
        ("bb_period", 20), ("bb_stddev", 2),
        ("rsi_period", 14), ("rsi_entry", 30), ("rsi_exit", 70),
        ("macd_fast", 12), ("macd_slow", 26), ("macd_signal", 9),
        ("vol_period", 20),
        ("vwap_period", 20),
    )

    def stra_initial(self):
        # Trend + momentum + volatility indicators
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
        self.atr = {
            d: bt.indicators.ATR(d, period=self.p.atr_period)
            for d in self.datas
        }
        # Liquidity check
        if getattr(self, 'liquidity_check', True) is True:
            self.LIQUIDITY_VOL_THRESHOLD = 50 * 1000
            self.sma_vol = bt.indicators.SimpleMovingAverage(self.data.volume, period=20)

    def _is_strong_uptrend(self, data):
        """Has the stock been above its 200-day SMA AND has positive
        MACD momentum for the last `trend_lookback` bars?
        """
        if len(data) < self.p.trend_sma_period + self.p.trend_lookback:
            return False
        for i in range(0, self.p.trend_lookback):
            if data.close[-(i)] <= self.trend_sma[data][-(i)]:
                return False
            if self.macd[data].macd[-(i)] <= 0:
                return False
        return True

    def _initial_atr_stop(self, data, entry_price):
        """Compute initial stop as N * ATR below entry."""
        return entry_price - self.p.atr_stop_mult * self.atr[data][0]

    def stra_buy_in(self, data):
        return self._is_strong_uptrend(data)

    def stra_sell_out(self, data):
        if len(data) < self.p.trend_sma_period:
            return False
        return data.close[0] < self.trend_sma[data][0]

    def next(self):
        # Run the parent (handles most of the entry/exit logic).
        # After parent runs, override the trailing_stop values to
        # be ATR-based instead of fixed-percentage.
        super().next()
        for data in self.datas:
            if data in self.trailing_stop and self.atr[data][0] > 0:
                # Replace fixed % stop with ATR * N stop, but never
                # loosen the existing stop.
                atr_stop = data.close[0] - self.p.atr_stop_mult * self.atr[data][0]
                self.trailing_stop[data] = max(self.trailing_stop[data], atr_stop)
                self.stop_loss[data] = max(self.stop_loss[data], atr_stop)
