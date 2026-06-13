"""
Donchian / Turtle breakout — the original trend-following system.

Reference
---------
- Richard Donchian (1970s) — Donchian Channels
- Curtis Faith (2003) — "Way of the Turtle", the canonical book
  on the original Turtle Trading system.
- The original Turtle S1 system used 20-day entry / 10-day exit
  with 2N ATR stops. S2 used 55/20 with 2N stops.

This implementation uses the Donchian channel as the entry/exit
signal and a percentage trailing stop. We skip the 2N ATR stop
because Backtrader's `MovingProfitStrategy` already gives us a
percent trailing stop (and the 2N ATR scaling is similar in
spirit — volatility-adjusted).

Logic
-----
Entry: close > highest_high(N_entry) over the last N_entry bars
       (breakout to new N-day high)
Exit:  close < lowest_low(N_exit) over the last N_exit bars
       (breakdown to new N-day low)

Parameters to tune
------------------
  - entry_period: 20 (S1) or 55 (S2)
  - exit_period:  10 (S1) or 20 (S2)
  - trailing_stop_pct: 12% (default, no TP)
  - skip_first_n: how many bars to skip (e.g. 30) to avoid first
                  breakout being on the leftmost bar of the window

Why this is famous
------------------
Fidelity's original Turtle experiment (1983-1988) reportedly
turned $5M into $100M+ for Richard Dennis. The system is the
archetype of trend-following and remains the basis of many
CTAs (Commodity Trading Advisors) like Man Investments,
Winton Group, etc.
"""
import backtrader as bt
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy


class DonchianStrategy(MovingProfitStrategy):
    """
    Donchian breakout (Turtle S1/S2 style) with trailing stop.
    """

    NAME = "Donchian"

    params = (
        # Donchian channel periods
        ("entry_period", 20),  # 20-day high for entry (S1)
        ("exit_period", 10),   # 10-day low for exit (S1)

        # Trailing stop / TP
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.12),
        ("trailing_takeprofit_pct", 0.99),
    )

    def stra_initial(self):
        # Highest high and lowest low over the lookback windows
        self.hh = {
            d: bt.indicators.Highest(d.high, period=self.p.entry_period)
            for d in self.datas
        }
        self.ll = {
            d: bt.indicators.Lowest(d.low, period=self.p.exit_period)
            for d in self.datas
        }

    def _breakout_up(self, data):
        """Close breaks above the N-day high (excluding the current bar).

        We use the previous bar's HH to avoid the trivial case of
        `high[0] == hh[0]` always being true on the bar that sets
        the new high.
        """
        if len(data) < self.p.entry_period + 1:
            return False
        return data.close[0] > self.hh[data][-1]

    def _breakdown(self, data):
        """Close breaks below the N-day low (excluding the current bar)."""
        if len(data) < self.p.exit_period + 1:
            return False
        return data.close[0] < self.ll[data][-1]

    def stra_buy_in(self, data):
        return self._breakout_up(data)

    def stra_sell_out(self, data):
        return self._breakdown(data)
