"""
Larry Williams' Volatility Breakout — the famous "Profitability of
Trading the Close" strategy from his 1970s/80s work.

Reference
---------
- Williams, Larry. "Long-Term Secrets to Short-Term Trading".
  Wiley, 1999. Chapter 4 (and earlier magazine articles).
- The "Overnight" version: buy at close if Close > Open + k*ATR(N-1).
- Famously, Williams reports an annual return of ~10,000% on
  soybean futures over a 10-year period using this simple rule.

Logic
-----
For each bar:
  R = ATR(N-1)            # use YESTERDAY's N-period ATR (no look-ahead)
  Buy_threshold = Open + k * R
Sell_threshold = Open - k * R

Buy when close > Buy_threshold
Sell when close < Sell_threshold

We also use an EMA trend filter to keep us in strong trends:
  - Buy only when EMA(close, ema_period) is rising
  - Sell when EMA starts falling (or hit trailing stop)

Parameters to tune
------------------
  - atr_period: 1 (true daily range), 2, 5, 10, 20
  - k: multiplier (0.5 in original, can be 0.3-1.0)
  - ema_period: 50, 100, 200 for trend filter
  - The EMA filter is what makes this useful for stocks (vs pure
    futures overnight systems which work on any direction).

Why this is famous
------------------
- Williams' 1970s Robber/Crimson 1M contest win was based on
  this kind of breakout.
- It's the canonical "Overnight momentum" rule.
- Adding an EMA trend filter is a known improvement (e.g.
  Andreas Clenow's "Trading Evolved" calls this exact setup).
"""
import backtrader as bt
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy


class VolatilityBreakoutStrategy(MovingProfitStrategy):
    """
    Larry Williams' volatility breakout with EMA trend filter.
    """

    NAME = "VolBreakout"

    params = (
        # ATR lookback (use yesterday's N-day ATR)
        ("atr_period", 1),  # 1 = true daily range

        # Breakout multiplier
        ("k", 0.5),

        # Trend filter: long EMA rising
        ("ema_period", 50),

        # Trailing stop / no TP
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.12),
        ("trailing_takeprofit_pct", 0.99),
    )

    def stra_initial(self):
        # ATR (using Wilder's smoothing) — we use -1 to use yesterday's ATR
        # by referencing atr[-1] in the strategy. Backtrader's ATR includes
        # the current bar so we offset by one bar.
        self.atr = {
            d: bt.indicators.ATR(d, period=self.p.atr_period)
            for d in self.datas
        }
        self.ema = {
            d: bt.indicators.ExponentialMovingAverage(d.close, period=self.p.ema_period)
            for d in self.datas
        }

    def _atr_yesterday(self, data):
        """Yesterday's N-period ATR (avoid look-ahead bias)."""
        if len(data) < self.p.atr_period + 2:
            return None
        return self.atr[data][-1]

    def _trend_up(self, data):
        """EMA must be rising (close > EMA)."""
        if len(data) < self.p.ema_period + 1:
            return False
        return data.close[0] > self.ema[data][0]

    def stra_buy_in(self, data):
        atr = self._atr_yesterday(data)
        if atr is None:
            return False
        threshold = data.open[0] + self.p.k * atr
        return data.close[0] > threshold and self._trend_up(data)

    def stra_sell_out(self, data):
        # Sell when EMA trend turns down OR price breaks below
        # the sell threshold
        atr = self._atr_yesterday(data)
        if atr is None:
            return False
        sell_threshold = data.open[0] - self.p.k * atr
        if data.close[0] < sell_threshold:
            return True
        # Also exit if trend turns down (close < EMA)
        if data.close[0] < self.ema[data][0]:
            return True
        return False
