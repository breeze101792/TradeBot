"""
HPTrend on Heikin Ashi close — HP filter on smoothed candle close.

Heikin Ashi is a Japanese candlestick transform that smooths out
1-bar noise by using the previous HA close in the new bar's open:

  HA_Close = (Open + High + Low + Close) / 4
  HA_Open  = (prev_HA_Open + prev_HA_Close) / 2

Hypothesis: applying HP to HA close (instead of raw close) gives
a doubly-smoothed trend. This should reduce whipsaw further.

Alternative: HP on typical price (H+L+C)/3, which down-weights
the wicks. Should be similar but slightly more responsive.
"""
import backtrader as bt
import numpy as np
from utility.debug import *
from strategy.candidate.multisignal import MultiSignalStrategy
from strategy.ai.hptrend import HPFilter


class HPTrendHAStrategy(MultiSignalStrategy):
    """HPTrend on Heikin Ashi close (HA close is the (O+H+L+C)/4 average)."""

    NAME = "HPTrendHA"

    params = (
        # HP filter — same as HPTrend
        ("hp_lookback", 90),
        ("hp_lambda", 1e5),
        ("slope_lookback", 3),
        # Trailing stop / no TP
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.12),
        ("trailing_takeprofit_pct", 0.99),
        # Inherited
        ("bb_period", 20), ("bb_stddev", 2),
        ("rsi_period", 14), ("rsi_entry", 30), ("rsi_exit", 70),
        ("macd_fast", 12), ("macd_slow", 26), ("macd_signal", 9),
        ("vol_period", 20),
        ("vwap_period", 20),
    )

    def stra_initial(self):
        super().stra_initial()
        self.hp_filter = HPFilter(lam=self.p.hp_lambda)
        self._price_history = {d: [] for d in self.datas}
        self._hp_trend = {d: [] for d in self.datas}
        # Track raw OHLC for HA close calculation
        self._raw = {d: [] for d in self.datas}

    def next(self):
        for data in self.datas:
            try:
                o = data.open[0]
                h = data.high[0]
                l = data.low[0]
                c = data.close[0]
            except IndexError:
                continue
            self._raw[data].append((o, h, l, c))
            if len(self._raw[data]) > self.p.hp_lookback:
                self._raw[data].pop(0)
            # Compute HA close: (O+H+L+C)/4 (also save the smoothed close itself)
            if len(self._raw[data]) >= 30:
                ha_close = [(r[0] + r[1] + r[2] + r[3]) / 4 for r in self._raw[data]]
                trend = self.hp_filter.filter(ha_close)
                self._hp_trend[data] = list(trend)
                self._price_history[data] = ha_close
            else:
                self._hp_trend[data] = []
        super().next()

    def _is_strong_uptrend(self, data):
        if data not in self._hp_trend or len(self._hp_trend[data]) < self.p.slope_lookback + 1:
            return False
        for i in range(0, self.p.slope_lookback):
            curr = self._hp_trend[data][-(i + 1)]
            prev = self._hp_trend[data][-(i + 2)] if i + 2 <= len(self._hp_trend[data]) else curr
            if curr <= prev:
                return False
        return True

    def stra_buy_in(self, data):
        if self._is_strong_uptrend(data):
            return True
        return super().stra_buy_in(data)

    def stra_sell_out(self, data):
        if self._is_strong_uptrend(data):
            return False
        return super().stra_sell_out(data)
