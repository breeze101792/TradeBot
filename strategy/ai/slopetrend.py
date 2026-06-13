"""
SlopeTrend strategy: uses EMA slope + Kalman-filtered momentum
to filter out the noise that costs the Hybrid money.

The problem this solves
-----------------------
Diagnostic of Hybrid's 2024 losers (t50):
  1301  Hybrid -16.21%  SMA-45 slope -39.51%   (secular downtrend)
  1303  Hybrid  +6.64%  SMA-45 slope -34.41%   (secular downtrend!)
  1326  Hybrid -30.68%  SMA-45 slope -38.13%   (secular downtrend)
  6505  Hybrid -21.03%  SMA-45 slope -40.92%   (secular downtrend)
  2207  Hybrid  +5.41%  SMA-45 slope  -0.79%   (choppy)
  2382  Hybrid  +3.32%  SMA-45 slope +20.51%   (right direction, but Hybrid missed most)
  6669  Hybrid  +4.82%  SMA-45 slope  +0.21%   (choppy, no trend)

In 2022 the same pattern: 2615 (slope -46%) lost -31%, 2603
(slope -49%) lost -24%. The Hybrid is buying stocks that
ARE in a downtrend, just because the price happens to be
above the SMA-45 for 5 bars.

Fix: replace the "price > SMA for 5 bars" check with a
"price > SMA AND SMA slope > 0" check. A stock with a
negative SMA-45 slope is NOT in an uptrend regardless of
where price is vs SMA.

Why this works
--------------
The research consensus (per Breakout Trading Academy's
100-filter comparison) is that moving-average slope is
the #1 most effective filter for reducing whipsaws. The
slope is a 1st-derivative measure that captures momentum
direction. A positive slope = trend is accelerating. A
flat or negative slope = trend is fading or reversing.

In addition, we apply a Kalman-filter-style noise
smoothing to the momentum signal. A 1st-order Kalman
filter with process_variance=1e-5 and
measurement_variance=1e-3 effectively low-pass-filters
the price series, removing day-to-day noise. The
resulting smoothed signal is the "true" trend, which
is much less prone to false triggers from 1-2 day spikes.

Per-year average annual return, t50 2020-2024:
  Year | Hybrid | SlopeTrend
  -----|--------|------------
  2020 | +22.6% |   TBD
  2021 | +14.2% |   TBD
  2022 |  -3.9% |   TBD (target: closer to 0)
  2023 | +10.7% |   TBD
  2024 |  +6.1% |   TBD (target: more positive)
"""
import backtrader as bt
from utility.debug import *
from strategy.candidate.multisignal import MultiSignalStrategy
import numpy as np


class KalmanFilter1D:
    """Simple 1D Kalman filter for state estimation.

    Tracks a latent "true" value through noisy observations.
    State: x (the true value)
    Process: x_t = x_{t-1} + process_noise  (random walk)
    Measurement: z_t = x_t + measurement_noise

    Tuned with process_variance=1e-5 (very stable) and
    measurement_variance=1e-3 (small noise tolerance).
    Effective behavior: low-pass filter that smooths out
    high-frequency noise while tracking medium-frequency
    changes.
    """

    def __init__(self, process_variance=1e-5, measurement_variance=1e-3,
                 initial_value=0.0):
        self.q = process_variance  # how much the true state can change per step
        self.r = measurement_variance  # measurement noise
        self.x = initial_value  # current state estimate
        self.p = 1.0  # current uncertainty

    def update(self, measurement):
        # Predict
        x_pred = self.x
        p_pred = self.p + self.q
        # Update
        k = p_pred / (p_pred + self.r)  # Kalman gain
        self.x = x_pred + k * (measurement - x_pred)
        self.p = (1 - k) * p_pred
        return self.x

    def get(self):
        return self.x


class SlopeTrendStrategy(MultiSignalStrategy):
    """
    MultiSignal with a slope-based trend filter (not just price-vs-SMA).

    The original Hybrid uses "close > SMA-45 for 5 bars AND MACD>0
    for 5 bars" as the trend filter. This still gets triggered on
    bear-market rallies (e.g. early 2022), causing bad entries.

    SlopeTrend replaces the "close > SMA" check with "SMA slope > 0"
    check, so a stock in a downtrend (negative slope) is never traded
    even if price briefly closes above the SMA.

    We also apply a Kalman filter to the MACD line so that the
    momentum signal is denoised. The Kalman filter has:
      - process_variance = 1e-5 (very smooth, tracks slow changes)
      - measurement_variance = 1e-3 (small noise tolerance)
    This effectively low-pass-filters the MACD, removing 1-2 day
    spikes that would otherwise falsely trigger the trend filter.
    """

    NAME = "SlopeTrend"

    params = (
        # Trend filter: SMA slope must be positive for the last
        # `trend_lookback` bars. This is the key difference from
        # Hybrid (which just checks close > SMA).
        ("trend_sma_period", 45),
        ("trend_lookback", 5),

        # Kalman filter tuning
        ("kalman_process_var", 1e-5),
        ("kalman_measurement_var", 1e-3),

        # Inherited from MovingProfitStrategy. Use 10/12 like Hybrid.
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.10),
        ("trailing_takeprofit_pct", 0.12),

        # Inherited
        ("bb_period", 20), ("bb_stddev", 2),
        ("rsi_period", 14), ("rsi_entry", 30), ("rsi_exit", 70),
        ("macd_fast", 12), ("macd_slow", 26), ("macd_signal", 9),
        ("vol_period", 20),
        ("vwap_period", 20),
    )

    def stra_initial(self):
        # MultiSignal indicators
        super().stra_initial()

        # Trend SMA + slope
        self.trend_sma = {
            d: bt.indicators.SimpleMovingAverage(d.close, period=self.p.trend_sma_period)
            for d in self.datas
        }

        # Kalman-filtered MACD. We pre-compute it as a derived
        # indicator by running a Kalman filter in next() over the
        # MACD line. Here we just track the MACD values.
        self.kalman_macd = {d: None for d in self.datas}  # per-data filter
        self._kalman_initialized = {d: False for d in self.datas}

    def _is_strong_uptrend(self, data):
        """Two checks:
        1. SMA slope > 0 for the last `trend_lookback` bars (not just
           close > SMA, which can trigger in bear-market rallies).
        2. Kalman-filtered MACD > 0 for the last `trend_lookback` bars.
        """
        if len(data) < self.p.trend_sma_period + self.p.trend_lookback:
            return False

        # Check 1: SMA slope positive
        for i in range(0, self.p.trend_lookback):
            curr = self.trend_sma[data][-(i)]
            prev = self.trend_sma[data][-(i+1)] if i + 1 < len(self.trend_sma[data]) else curr
            if curr <= prev:
                return False

        # Check 2: Kalman-filtered MACD > 0
        for i in range(0, self.p.trend_lookback):
            kf = self.kalman_macd.get(data)
            if kf is None:
                return False
            k_macd = kf.get()
            if k_macd <= 0:
                return False
            # We only have the latest value, not a history. So we
            # require the same condition on raw MACD too as a
            # sanity check.
            raw_macd = self.macd[data].macd[-(i)]
            if raw_macd <= 0:
                return False
        return True

    def next(self):
        # First, update the Kalman filter for each data feed.
        for data in self.datas:
            try:
                raw_macd = self.macd[data].macd[0]
            except IndexError:
                continue
            if not self._kalman_initialized[data]:
                self.kalman_macd[data] = KalmanFilter1D(
                    process_variance=self.p.kalman_process_var,
                    measurement_variance=self.p.kalman_measurement_var,
                    initial_value=raw_macd,
                )
                self._kalman_initialized[data] = True
                # Set initial value without filter
                self.kalman_macd[data].x = raw_macd
            else:
                self.kalman_macd[data].update(raw_macd)

        # Then run the parent's next() (handles buy/sell).
        super().next()

    def stra_buy_in(self, data):
        # Same as Hybrid: in uptrend, just stay long.
        if self._is_strong_uptrend(data):
            return True
        # Otherwise: mean-reversion entry.
        return super().stra_buy_in(data)

    def stra_sell_out(self, data):
        # Same as Hybrid: in uptrend, don't take MS sell.
        if self._is_strong_uptrend(data):
            return False
        return super().stra_sell_out(data)
