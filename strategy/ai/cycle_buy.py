"""
CycleBuy — buy at cycle troughs within an HP-confirmed uptrend.

DPO (Detrended Price Oscillator) strips out the trend by subtracting
a moving average shifted by half the period, leaving the pure
cyclical component. A 20-day DPO shows the 20-40 day price cycle.

Strategy:
  - HP filter confirms we're in an uptrend (long-term direction).
  - DPO < threshold (cycle trough): the price is at the bottom
    of its short-term cycle, which is a good time to enter
    because the next move is likely up.
  - Exit when HP slope turns negative (trend break) OR price
    is up enough to warrant a stop-triggered exit.

This is "buy the dip in a confirmed uptrend" — opposite of
trend-following in a sense. We're using HP for direction
(weekly/monthly) but DPO for timing (daily/weekly).
"""
import backtrader as bt
import numpy as np
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy
from strategy.ai.hptrend import HPFilter


class CycleBuyStrategy(MovingProfitStrategy):
    """Buy at cycle troughs when HP confirms long-term uptrend."""

    NAME = "CycleBuy"

    params = (
        # HP filter for long-term trend direction
        ("hp_lookback", 90),
        ("hp_lambda", 1e5),
        ("hp_slope_lookback", 3),
        # DPO for cycle timing
        ("dpo_period", 20),
        # DPO threshold: -X means "price is X% below its detrended
        # baseline" = cycle trough.
        ("dpo_threshold", -0.02),  # -2%
        # Trailing stop / no TP
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.12),
        ("trailing_takeprofit_pct", 0.99),
    )

    def stra_initial(self):
        # HP filter
        self.hp_filter = HPFilter(lam=self.p.hp_lambda)
        self._price_history = {d: [] for d in self.datas}
        self._hp_trend = {d: [] for d in self.datas}

        # DPO uses a shifted SMA to strip out the trend
        # Standard DPO formula: DPO = close - SMA(close, period)[shift=period/2 + 1]
        # In backtrader, we can compute this directly with a moving average
        # and a shift.
        self.dpo_sma = {
            d: bt.indicators.SimpleMovingAverage(d.close, period=self.p.dpo_period)
            for d in self.datas
        }

    def next(self):
        for data in self.datas:
            try:
                close = data.close[0]
            except IndexError:
                continue
            self._price_history[data].append(close)
            if len(self._price_history[data]) > self.p.hp_lookback:
                self._price_history[data].pop(0)
            if len(self._price_history[data]) >= 30:
                trend = self.hp_filter.filter(self._price_history[data])
                self._hp_trend[data] = list(trend)
            else:
                self._hp_trend[data] = []
        super().next()

    def _hp_rising(self, data):
        if data not in self._hp_trend or len(self._hp_trend[data]) < self.p.hp_slope_lookback + 1:
            return False
        for i in range(self.p.hp_slope_lookback):
            curr = self._hp_trend[data][-(i + 1)]
            prev = self._hp_trend[data][-(i + 2)]
            if curr <= prev:
                return False
        return True

    def _dpo(self, data):
        """DPO = close - SMA(close, period) shifted back by period/2 + 1.

        In backtrader, the SMA at index -(period/2+1) gives us the
        shifted value. We then take the difference and normalize by
        the shifted SMA.
        """
        shift = self.p.dpo_period // 2 + 1
        if len(data) < self.p.dpo_period + shift:
            return 0.0
        try:
            sma_shifted = self.dpo_sma[data][-shift]
            if sma_shifted == 0:
                return 0.0
            return (data.close[0] - sma_shifted) / sma_shifted
        except IndexError:
            return 0.0

    def stra_buy_in(self, data):
        # HP must be rising (long-term uptrend)
        if not self._hp_rising(data):
            return False
        # DPO must be below threshold (cycle trough)
        return self._dpo(data) < self.p.dpo_threshold

    def stra_sell_out(self, data):
        # Exit when HP slope turns negative
        return not self._hp_rising(data)
