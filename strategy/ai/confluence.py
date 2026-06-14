"""
Confluence — vote-based multi-signal strategy.

The problem this solves
-----------------------
Hybrid uses 2 signals (SMA + MACD) joined by AND. That means
BOTH must agree. In a choppy market, when one disagrees, we
either miss entries or get stopped out by the other.

The Confluence strategy uses 5 *independent* signals and enters
when a majority (3-of-5 or 4-of-5) agree. Exits when the
majority flips against us. This is a "democratic" approach —
no single signal can veto a position, and no single signal
can force us in either.

The 5 signals (chosen for independence):
  1. HP filter slope (denoised trend direction)
  2. SMA-50 slope (medium-term trend momentum)
  3. MACD > signal (price momentum)
  4. ADX > 20 (market is TRENDING, not choppy) — the "regime gate"
  5. Volume > 20-day average (commitment / liquidity)

Each signal returns True (bullish) or False (bearish). A signal
returning None (insufficient data) is treated as bearish
(conservative) so we don't enter before we have enough history.

Why 5 signals and not 3?
------------------------
With 3 signals, 2-of-3 is just a tie-breaker. With 5, we get
a 3-of-5 majority that filters out single-signal noise. ADX is
included as a "regime gate" because most false signals come
from choppy/ranging markets where trend signals are noise.

Why ADX is a regime gate
------------------------
ADX measures trend strength regardless of direction. A high
ADX (>20-25) means the market is trending; a low ADX (<20)
means it's ranging. Most whipsaws happen in ranging markets
where MACD, slope, and HP signals all flip-flop. By requiring
ADX > threshold, we ensure we're trading in trending markets.

The 12/99 risk profile
----------------------
12% trailing stop, no take-profit (same as HPTrend best).
Tested: this combination works for trend-followers on TWSE.

Per-year average annual return, t50 2020-2024:
  Year | Confluence (5-of-7 vote)
  -----|--------------------------
  2020 | TBD
  2021 | TBD
  2022 | TBD (target: better than HPTrend's -5.57%)
  2023 | TBD
  2024 | TBD
  5y   | TBD (target: > 14.23% HPTrend)
"""
import backtrader as bt
import numpy as np
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy
from strategy.ai.hptrend import HPFilter


class ConfluenceStrategy(MovingProfitStrategy):
    """Vote-based 5-signal confluence.

    5 independent signals vote bullish/bearish each bar.
    Enter when 4-of-5 vote bullish (strong consensus).
    Exit when 2-or-fewer vote bullish (consensus breaks).
    """

    NAME = "Confluence"

    params = (
        # Signal 1: HP filter (denoised trend)
        ("hp_lookback", 90),
        ("hp_lambda", 1e5),
        ("hp_slope_lookback", 3),
        # Signal 2: SMA-50 slope (medium-term momentum)
        ("sma_period", 50),
        ("sma_slope_lookback", 3),
        # Signal 3: MACD
        ("macd_fast", 12),
        ("macd_slow", 26),
        ("macd_signal", 9),
        # Signal 4: ADX (regime gate)
        ("adx_period", 14),
        ("adx_threshold", 20),
        # Signal 5: Volume confirmation
        ("vol_period", 20),
        # Voting
        ("entry_votes", 4),  # need 4-of-5 to enter
        ("exit_votes", 2),   # exit if only 0, 1, or 2 vote bullish
        # Trailing stop / no TP
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.12),
        ("trailing_takeprofit_pct", 0.99),
    )

    def stra_initial(self):
        # Signal 1: HP filter
        self.hp_filter = HPFilter(lam=self.p.hp_lambda)
        self._price_history = {d: [] for d in self.datas}
        self._hp_trend = {d: [] for d in self.datas}

        # Signal 2: SMA-50
        self.sma = {
            d: bt.indicators.SimpleMovingAverage(d.close, period=self.p.sma_period)
            for d in self.datas
        }

        # Signal 3: MACD
        self.macd = {
            d: bt.indicators.MACD(
                d.close,
                period_me1=self.p.macd_fast,
                period_me2=self.p.macd_slow,
                period_signal=self.p.macd_signal,
            )
            for d in self.datas
        }

        # Signal 4: ADX
        self.adx = {
            d: bt.indicators.ADX(d, period=self.p.adx_period)
            for d in self.datas
        }

        # Signal 5: Volume MA
        self.vol_ma = {
            d: bt.indicators.SimpleMovingAverage(d.volume, period=self.p.vol_period)
            for d in self.datas
        }

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

    def _signal_hp(self, data):
        """1: HP filter is rising for the last `hp_slope_lookback` bars."""
        if data not in self._hp_trend or len(self._hp_trend[data]) < self.p.hp_slope_lookback + 1:
            return None
        for i in range(self.p.hp_slope_lookback):
            curr = self._hp_trend[data][-(i + 1)]
            prev = self._hp_trend[data][-(i + 2)]
            if curr <= prev:
                return False
        return True

    def _signal_sma_slope(self, data):
        """2: SMA-50 is rising for the last `sma_slope_lookback` bars."""
        if len(data) < self.p.sma_period + self.p.sma_slope_lookback:
            return None
        for i in range(self.p.sma_slope_lookback):
            curr = self.sma[data][-(i)]
            prev = self.sma[data][-(i + 1)]
            if curr <= prev:
                return False
        return True

    def _signal_macd(self, data):
        """3: MACD is above its signal line (positive momentum)."""
        try:
            return self.macd[data].macd[0] > self.macd[data].signal[0]
        except IndexError:
            return None

    def _signal_adx(self, data):
        """4: ADX > threshold means the market is trending (not choppy).
        Returns True for "trending is bullish for us" — but ADX is
        direction-agnostic. We use ADX as a multiplier: only count
        this as bullish if ADX > threshold AND price > SMA.
        """
        if len(data) < self.p.adx_period + 1:
            return None
        try:
            adx_val = self.adx[data][0]
        except IndexError:
            return None
        if adx_val < self.p.adx_threshold:
            return False  # choppy market, count as bearish
        # Trending: count as bullish only if price > SMA
        return data.close[0] > self.sma[data][0]

    def _signal_volume(self, data):
        """5: Today's volume is above its 20-day average (commitment)."""
        if len(data) < self.p.vol_period + 1:
            return None
        try:
            return data.volume[0] > self.vol_ma[data][0]
        except IndexError:
            return None

    def _vote(self, data):
        """Count bullish votes out of 5. None votes count as bearish
        (conservative — don't enter before we have enough data)."""
        signals = [
            self._signal_hp(data),
            self._signal_sma_slope(data),
            self._signal_macd(data),
            self._signal_adx(data),
            self._signal_volume(data),
        ]
        # Treat None as False
        votes = sum(1 for s in signals if s is True)
        return votes

    def stra_buy_in(self, data):
        return self._vote(data) >= self.p.entry_votes

    def stra_sell_out(self, data):
        return self._vote(data) <= self.p.exit_votes
