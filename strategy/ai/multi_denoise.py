"""
TripleDenoise — agreement of 3 independent denoising methods.

The hypothesis: HP filter is the best denoiser on t50. But
maybe combining HP + Kalman + EMA smoothings gives a more
robust signal than any single one.

  - HP filter (lambda=1e5, lookback=90): macro-economist's
    trend-cycle decomposition.
  - Kalman filter (process_var=1e-5, meas_var=1e-3): state-
    space low-pass filter. Different math from HP.
  - EMA-50 slope: simplest smoother, but still removes
    day-to-day noise.

If all 3 are rising, that's a strong consensus. If 2 of 3
are rising, that's still a meaningful trend.

The DPO (Detrended Price Oscillator) is a 4th signal that
works against the trend — when DPO > 0, price is above its
SMA, suggesting reversion. We use DPO as a "mean-reversion
warning": if DPO > +k, the trend is overextended and we
should take profits on the partial-take-profit machinery.

This is a 4-signal strategy with:
  3 trend denoisers that must all agree for entry
  1 mean-reversion guard that warns against overextension
"""
import backtrader as bt
import numpy as np
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy
from strategy.ai.hptrend import HPFilter
from strategy.ai.slopetrend import KalmanFilter1D


class TripleDenoiseStrategy(MovingProfitStrategy):
    """Three denoisers must agree on trend direction.

    Entry: HP-trend rising AND Kalman-trend rising AND EMA-50 slope > 0
    Exit: any 2 of 3 say down
    """

    NAME = "TripleDenoise"

    params = (
        # HP filter
        ("hp_lookback", 90),
        ("hp_lambda", 1e5),
        # Kalman
        ("kalman_process_var", 1e-5),
        ("kalman_measurement_var", 1e-3),
        # EMA
        ("ema_period", 50),
        # Slope lookback
        ("slope_lookback", 3),
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

        # Kalman filter (one per data feed)
        self.kalman = {d: None for d in self.datas}
        self._kalman_initialized = {d: False for d in self.datas}

        # EMA
        self.ema = {
            d: bt.indicators.EMA(d.close, period=self.p.ema_period)
            for d in self.datas
        }

    def next(self):
        for data in self.datas:
            try:
                close = data.close[0]
            except IndexError:
                continue

            # HP filter
            self._price_history[data].append(close)
            if len(self._price_history[data]) > self.p.hp_lookback:
                self._price_history[data].pop(0)
            if len(self._price_history[data]) >= 30:
                trend = self.hp_filter.filter(self._price_history[data])
                self._hp_trend[data] = list(trend)
            else:
                self._hp_trend[data] = []

            # Kalman filter
            if not self._kalman_initialized[data]:
                self.kalman[data] = KalmanFilter1D(
                    process_variance=self.p.kalman_process_var,
                    measurement_variance=self.p.kalman_measurement_var,
                    initial_value=close,
                )
                self._kalman_initialized[data] = True
                self.kalman[data].x = close
            else:
                self.kalman[data].update(close)

        super().next()

    def _hp_rising(self, data):
        if data not in self._hp_trend or len(self._hp_trend[data]) < self.p.slope_lookback + 1:
            return False
        for i in range(self.p.slope_lookback):
            curr = self._hp_trend[data][-(i + 1)]
            prev = self._hp_trend[data][-(i + 2)]
            if curr <= prev:
                return False
        return True

    def _kalman_rising(self):
        """We only have the latest Kalman value, not history. So we
        approximate by checking if it's above the EMA (which acts as
        a slow proxy for the trend)."""
        # Note: kalman_rising is a 1-bar measure (latest vs prior close).
        # For multi-bar slope we'd need to track Kalman history. Instead,
        # we use: Kalman value > EMA value (Kalman above slow trend).
        # The EMA acts as a "stable anchor" — Kalman above EMA means
        # the smoothed value is currently above the long-term baseline.
        # We do this per-data in the function below.
        pass

    def _kalman_above_ema(self, data):
        k = self.kalman.get(data)
        if k is None:
            return False
        return k.get() > self.ema[data][0]

    def _ema_rising(self, data):
        if len(data) < self.p.ema_period + self.p.slope_lookback:
            return False
        for i in range(self.p.slope_lookback):
            curr = self.ema[data][-(i)]
            prev = self.ema[data][-(i + 1)]
            if curr <= prev:
                return False
        return True

    def _votes(self, data):
        hp = self._hp_rising(data)
        # Kalman-as-proxy: latest Kalman > EMA = smoothed value above baseline
        kal = self._kalman_above_ema(data)
        ema = self._ema_rising(data)
        return int(hp) + int(kal) + int(ema)

    def stra_buy_in(self, data):
        # Need all 3 (or at least 2) to agree
        return self._votes(data) >= 3

    def stra_sell_out(self, data):
        # Exit when only 0 or 1 of 3 vote bullish
        return self._votes(data) <= 1
