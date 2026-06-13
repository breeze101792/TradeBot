"""
Dual Thrust — Michael Chiu's classic futures breakout system.

Reference
---------
- Chiu, Michael. "Day Trade the S&P 500 Index Futures with a
  Mechanical Trading System". Active Trader magazine, 1997.
- One of the most successful systematic futures strategies,
  widely used by retail and prop traders.

Logic
-----
Range: R = max(HH - LC, HC - LC, HH - LC) over N days
       (equivalently, R = max(HH, LC) - min(LC, HC) but standard
       formulation is:
        R = max(HH_n - CLOSE_n, HH_n - OPEN_n, OPEN_n - LL_n, CLOSE_n - LL_n)
       i.e. the largest 1-bar range over the N-day window, where
       each 1-bar range is max(H,L,O,C) - min(H,L,O,C))

Buy threshold:  Open_{today} + k1 * R
Sell threshold: Open_{today} - k2 * R

Buy when close > buy_threshold
Sell when close < sell_threshold
(or close position when low < sell_threshold during the day)

Parameters to tune
------------------
  - n: lookback for the range calculation (default 4 or 5)
  - k1: upper breakout multiplier (default 0.5 in original)
  - k2: lower breakout multiplier (default 0.5)
  - The original uses k1=k2 (symmetric), but Chiu showed
    asymmetric k1 != k2 can improve by allowing different
    breakout strengths in each direction.

Why this is famous
------------------
The Dual Thrust is one of the oldest (1997) and most-copied
futures strategies. It's still used today because:
  1. Simple — only 3 parameters.
  2. Robust — works across stocks, futures, FX, crypto.
  3. Adaptive — uses yesterday's range so it scales with volatility.
"""
import backtrader as bt
import numpy as np
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy


class DualThrustStrategy(MovingProfitStrategy):
    """
    Dual Thrust breakout. Buy when close > Open + k1*Range, sell
    when close < Open - k2*Range.
    """

    NAME = "DualThrust"

    params = (
        # Range lookback (the "N" in Dual Thrust)
        ("range_period", 4),

        # Breakout multipliers (original uses 0.5 / 0.5)
        ("k1", 0.5),
        ("k2", 0.5),

        # Trailing stop / TP (no TP, hold winners)
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.12),
        ("trailing_takeprofit_pct", 0.99),
    )

    def stra_initial(self):
        # We need the range data, so we'll compute it on the fly
        # in next() rather than using a Backtrader indicator.
        # Cache: data -> list of (h, l, o, c) tuples
        self._bars = {d: [] for d in self.datas}

    def next(self):
        # Update bar cache
        for data in self.datas:
            try:
                h = data.high[0]
                l = data.low[0]
                o = data.open[0]
                c = data.close[0]
            except IndexError:
                continue
            self._bars[data].append((h, l, o, c))
            # Trim to range_period
            if len(self._bars[data]) > self.p.range_period:
                self._bars[data].pop(0)

        super().next()

    def _range(self, data):
        """Range R = max(1-bar range over the lookback window).

        For each bar in the lookback, compute max(H,L,O,C) - min(H,L,O,C).
        Take the max of these.
        """
        if len(self._bars[data]) < self.p.range_period:
            return None
        bars = self._bars[data][-self.p.range_period:]
        max_range = 0.0
        for h, l, o, c in bars:
            r = max(h, l, o, c) - min(h, l, o, c)
            if r > max_range:
                max_range = r
        return max_range

    def _buy_threshold(self, data):
        R = self._range(data)
        if R is None:
            return None
        return data.open[0] + self.p.k1 * R

    def _sell_threshold(self, data):
        R = self._range(data)
        if R is None:
            return None
        return data.open[0] - self.p.k2 * R

    def stra_buy_in(self, data):
        threshold = self._buy_threshold(data)
        if threshold is None:
            return False
        return data.close[0] > threshold

    def stra_sell_out(self, data):
        threshold = self._sell_threshold(data)
        if threshold is None:
            return False
        return data.close[0] < threshold
