"""
Keltner Channel — volatility-based envelope using ATR.

A 20-day EMA middle band with bands at k*ATR above/below.
Entry on close > upper band (strong upward break); exit on close < lower band.

This is a well-known TA channel strategy. It's similar to Bollinger Bands
but uses ATR instead of standard deviation. The ATR-based bands make it
more responsive to sudden volatility changes.
"""
import backtrader as bt
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy


class KeltnerChannelStrategy(MovingProfitStrategy):
    """Keltner Channel breakout strategy.

    Buy:  close > upper band (EMA + k*ATR)
    Sell: close < lower band (EMA - k*ATR)
    """
    NAME = "Keltner"

    params = (
        # EMA period for the middle band
        ("ema_period", 20),
        # ATR period for band width
        ("atr_period", 10),
        # ATR multiplier
        ("k", 1.5),
        # Trailing stop / no TP
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.12),
        ("trailing_takeprofit_pct", 0.99),
    )

    def stra_initial(self):
        self.ema = {d: bt.indicators.EMA(d.close, period=self.p.ema_period) for d in self.datas}
        self.atr = {d: bt.indicators.ATR(d, period=self.p.atr_period) for d in self.datas}

    def _upper(self, data):
        return self.ema[data][0] + self.p.k * self.atr[data][0]

    def _lower(self, data):
        return self.ema[data][0] - self.p.k * self.atr[data][0]

    def stra_buy_in(self, data):
        if len(data) < max(self.p.ema_period, self.p.atr_period) + 1:
            return False
        return data.close[0] > self._upper(data)

    def stra_sell_out(self, data):
        if len(data) < max(self.p.ema_period, self.p.atr_period) + 1:
            return False
        return data.close[0] < self._lower(data)
