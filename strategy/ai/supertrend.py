"""
Supertrend — a famous trend indicator from the Indian stock market.

Reference
---------
- Olivier Seban (mid-2000s) — original Supertrend.
- Widely used in Indian markets, FX, and crypto.

Logic
-----
  Upper Band = (High + Low) / 2 + multiplier * ATR
  Lower Band = (High + Low) / 2 - multiplier * ATR

  When close > Upper Band: trend = up (buy)
  When close < Lower Band: trend = down (sell)

The bands "flip" — when the trend is up, the Lower Band is the
support; when trend is down, the Upper Band is the resistance.

Standard parameters
-------------------
  - atr_period: 10 (standard)
  - multiplier: 3.0 (standard)

Why it's famous
---------------
SuperTrend is the most-watched indicator on TradingView and
similar platforms. Indian retail traders use it heavily. It
combines trend direction with volatility-adjusted bands, so it
adapts to both quiet and volatile markets.
"""
import backtrader as bt
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy


class SuperTrendStrategy(MovingProfitStrategy):
    """
    Supertrend indicator with no take-profit.
    """

    NAME = "SuperTrend"

    params = (
        # ATR period
        ("atr_period", 10),
        # ATR multiplier
        ("multiplier", 3.0),
        # Trailing stop / no TP
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.12),
        ("trailing_takeprofit_pct", 0.99),
    )

    def stra_initial(self):
        self.atr = {d: bt.indicators.ATR(d, period=self.p.atr_period) for d in self.datas}
        # We need the (high+low)/2 — the "median price"
        self.mp = {d: (d.high + d.low) / 2 for d in self.datas}

    def _supertrend(self, data):
        """Compute SuperTrend direction.

        Returns: 1 if uptrend, -1 if downtrend, 0 if not enough data.
        """
        if len(data) < self.p.atr_period + 1:
            return 0
        atr = self.atr[data][0]
        mp = self.mp[data]
        upper = mp + self.p.multiplier * atr
        lower = mp - self.p.multiplier * atr

        # Use the close-based supertrend
        # Standard logic: if close > upper, flip to uptrend; if close < lower, flip to downtrend
        if data.close[0] > upper:
            return 1
        elif data.close[0] < lower:
            return -1
        else:
            # In the band — keep previous direction. We approximate by
            # checking if the close is above the midpoint.
            return 1 if data.close[0] > mp else -1

    def stra_buy_in(self, data):
        return self._supertrend(data) == 1

    def stra_sell_out(self, data):
        return self._supertrend(data) == -1
