"""
HP-Trend strategy: uses Hodrick-Prescott filter to denoise the
price series, then trades based on the smoothed trend component.

The problem this solves
-----------------------
The Hybrid strategy uses raw price + MACD as its signal. The
raw price oscillates around the "true" trend with daily
noise. This noise triggers false signals:

  - In uptrends: a 1-2 day pullback closes below the SMA-45
    and exits the strategy. The next day the trend resumes
    but the strategy has to re-enter at a higher price.
  - In bear-market rallies: a 1-2 day bounce closes above
    the SMA-45 and the strategy enters, just in time for
    the next leg down.

The HP (Hodrick-Prescott) filter is the standard
macro-economist's tool for separating trend from cycle. It
decomposes a time series y_t into:
  - trend_t: the smooth "true" trend (low-frequency)
  - cycle_t: the deviation (high-frequency noise)

with a penalty on cycle_t^2. The smoother parameter
controls the trade-off:
  - High lambda (e.g. 1e6): very smooth, slow to react
  - Low lambda (e.g. 1e4): follows price more closely

For daily stock data, lambda around 1e5 is a good default
(matches academic use for quarterly data scaled to daily).

The trade logic:
  - Buy when HP_trend is rising (slope > 0) AND HP_trend is
    above its recent level (momentum > 0).
  - Sell when HP_trend slope < 0 (trend break).
  - Mean-reversion entry (BB + RSI) when HP_trend is flat.

This eliminates the 1-2 day noise that fools the Hybrid.
A pullback in an uptrend is a small deviation in HP_trend
that doesn't break the slope>0 condition.
"""
import backtrader as bt
from utility.debug import *
from strategy.candidate.multisignal import MultiSignalStrategy
import numpy as np


class HPFilter:
    """Hodrick-Prescott filter.

    Decomposes a 1D time series y into trend + cycle.
    Minimizes:  sum (y_t - trend_t)^2  +  lambda * sum ((trend_{t+1} - trend_t) - (trend_t - trend_{t-1}))^2
    The first term fits the trend to the data; the second penalizes
    curvature in the trend (i.e. the trend should be smooth).
    """

    def __init__(self, lam=1e5):
        self.lam = lam

    def filter(self, y):
        """Compute HP trend. Solves the linear system via the
        standard 2nd-difference matrix trick.
        """
        y = np.asarray(y, dtype=float)
        n = len(y)
        if n < 4:
            return y.copy()
        # I + lam * K' K  where K is 2nd-diff operator
        # For n points, K is (n-2) x n
        # K'[i,j] = 1 if j==i or j==i+1 or j==i+2 (with signs)
        # We use sparse solver, but for small n direct solve is fine.
        I = np.eye(n)
        # Build K directly: K @ t = [t[i+2] - 2*t[i+1] + t[i] for i in range(n-2)]
        # K'K is tridiagonal with [1, -2, 1] in middle.
        KtK = np.zeros((n, n))
        for i in range(n - 2):
            KtK[i, i] += 1
            KtK[i, i + 1] += -2
            KtK[i, i + 2] += 1
            KtK[i + 1, i] += -2
            KtK[i + 1, i + 1] += 4
            KtK[i + 1, i + 2] += -2
            KtK[i + 2, i] += 1
            KtK[i + 2, i + 1] += -2
            KtK[i + 2, i + 2] += 1
        A = I + self.lam * KtK
        # Solve A @ trend = y
        trend = np.linalg.solve(A, y)
        return trend


class HPTrendStrategy(MultiSignalStrategy):
    """
    MultiSignal with a Hodrick-Prescott filtered trend.

    The trend filter checks the SLOPE of the HP-filtered price
    series rather than the raw price vs SMA. This eliminates
    the 1-2 day noise that the Hybrid's "close > SMA-45" check
    picks up.
    """

    NAME = "HPTrend"

    params = (
        # Lookback for HP filter
        ("hp_lookback", 90),  # use last 90 days for HP (best)
        ("hp_lambda", 1e5),  # smoothness parameter
        # Trend slope threshold (HP_trend must be rising)
        ("slope_lookback", 3),  # 2-5 all give ~14.2%, robust

        # Wider trailing stop + no take-profit (grid-search best).
        # The 12% stop lets through mid-trend pullbacks (8-12% is
        # normal in TWSE uptrends) but still protects against the
        # 2022-style 28% crash. Removing the 12% take-profit lets
        # winners run — this is the change that added ~3pp to the
        # 5y avg. With the old (10%, 12%) HPTrend, the strategy
        # sold 1/5 of the position at +12%, +24%, +36% in a
        # +60% rally (e.g. 2330 in 2020), then re-entered higher
        # up, missing 30+pp of upside. The 99% TP is effectively
        # "no take-profit" while still passing the
        # trailing_takeprofit > trailing_stop invariant.
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.12),  # 12% trailing stop (was 10%)
        ("trailing_takeprofit_pct", 0.99),  # no take-profit (was 12%)
        # Inherited
        ("bb_period", 20), ("bb_stddev", 2),
        ("rsi_period", 14), ("rsi_entry", 30), ("rsi_exit", 70),
        ("macd_fast", 12), ("macd_slow", 26), ("macd_signal", 9),
        ("vol_period", 20),
        ("vwap_period", 20),
    )

    def stra_initial(self):
        # MultiSignal indicators (which include MACD, BB, RSI, VWAP)
        super().stra_initial()

        # HP filter
        self.hp_filter = HPFilter(lam=self.p.hp_lambda)
        # Cache of close prices per data feed (for HP filter input)
        self._price_history = {d: [] for d in self.datas}
        # Cache of HP trend values per data feed
        self._hp_trend = {d: [] for d in self.datas}

    def next(self):
        # Update HP filter for each data feed
        for data in self.datas:
            try:
                close = data.close[0]
            except IndexError:
                continue
            self._price_history[data].append(close)
            if len(self._price_history[data]) > self.p.hp_lookback:
                self._price_history[data].pop(0)
            # Run HP filter if we have enough history
            if len(self._price_history[data]) >= 30:
                trend = self.hp_filter.filter(self._price_history[data])
                self._hp_trend[data] = list(trend)
            else:
                self._hp_trend[data] = []

        # Run the parent's next() (handles buy/sell)
        super().next()

    def _is_strong_uptrend(self, data):
        """HP trend must be rising for the last `slope_lookback` bars."""
        if data not in self._hp_trend or len(self._hp_trend[data]) < self.p.slope_lookback + 1:
            return False
        for i in range(0, self.p.slope_lookback):
            curr = self._hp_trend[data][-(i + 1)]
            prev = self._hp_trend[data][-(i + 2)] if i + 2 <= len(self._hp_trend[data]) else curr
            if curr <= prev:
                return False
        return True

    def stra_buy_in(self, data):
        # Same as Hybrid: in uptrend (now HP-based), just stay long.
        if self._is_strong_uptrend(data):
            return True
        # Otherwise: mean-reversion entry.
        return super().stra_buy_in(data)

    def stra_sell_out(self, data):
        # Same as Hybrid: in uptrend, don't take MS sell.
        if self._is_strong_uptrend(data):
            return False
        return super().stra_sell_out(data)
