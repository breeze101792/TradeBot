"""
KeltnerHP — Keltner Channel built on HP-filtered price.

Combines Keltner's volatility-adaptive bands with HP filter's
denoising. The HP filter smooths the close price, so the
EMA-of-HP (middle band) is much more stable than EMA-of-raw-close.
The ATR-based bands still adapt to current volatility.

Hypothesis: pure Keltner gets whipsawed by 1-2 day noise; HP-Keltner
rides the trend through noise like HPTrend does, but with wider
entry/exit thresholds from the ATR bands.
"""
import backtrader as bt
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy
from strategy.ai.hptrend import HPFilter


class KeltnerHPStrategy(MovingProfitStrategy):
    """Keltner Channel on HP-filtered price.

    The HP filter smooths the close, then the EMA + k*ATR bands
    form the entry/exit thresholds. Buy when HP-smoothed close
    breaks above the upper band; sell when it breaks below.
    """

    NAME = "KeltnerHP"

    params = (
        # HP filter
        ("hp_lookback", 90),
        ("hp_lambda", 1e5),
        # EMA + ATR for bands — long periods (grid-search best on t50/5y)
        ("ema_period", 50),
        ("atr_period", 20),
        ("k", 1.5),
        # Trailing stop / no TP
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.12),
        ("trailing_takeprofit_pct", 0.99),
    )

    def stra_initial(self):
        self.ema = {d: bt.indicators.EMA(d.close, period=self.p.ema_period) for d in self.datas}
        self.atr = {d: bt.indicators.ATR(d, period=self.p.atr_period) for d in self.datas}
        # HP filter
        self.hp_filter = HPFilter(lam=self.p.hp_lambda)
        self._price_history = {d: [] for d in self.datas}
        self._hp_trend = {d: [] for d in self.datas}

    def next(self):
        # Update HP filter
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

    def _hp_value(self, data):
        if not self._hp_trend[data]:
            return None
        return self._hp_trend[data][-1]

    def _upper(self, data):
        return self.ema[data][0] + self.p.k * self.atr[data][0]

    def _lower(self, data):
        return self.ema[data][0] - self.p.k * self.atr[data][0]

    def stra_buy_in(self, data):
        if len(data) < max(self.p.ema_period, self.p.atr_period) + 1:
            return False
        hp = self._hp_value(data)
        if hp is None:
            return False
        return hp > self._upper(data)

    def stra_sell_out(self, data):
        if len(data) < max(self.p.ema_period, self.p.atr_period) + 1:
            return False
        hp = self._hp_value(data)
        if hp is None:
            return False
        return hp < self._lower(data)
