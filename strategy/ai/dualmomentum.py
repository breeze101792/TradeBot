"""
DualMomentum (GEMS-style) — Gary Antonacci's famous strategy.

Reference
---------
Antonacci, Gary. "Dual Momentum Investing". McGraw-Hill, 2014.
The GEMS (Global Equities Momentum Screener) strategy:

  1. Compute 12-month (252-day) return for each stock.
  2. Rank the universe by this return.
  3. Hold the top-N stocks by momentum.
  4. Apply absolute momentum filter: only hold if stock is above
     its 200-day MA (i.e. 12-month MA in months, but here we use
     the 200-day SMA as a proxy for the long-term trend).
  5. If no stocks pass the absolute filter, sit in cash.

Why this is famous
------------------
Antonacci showed GEMS-style dual momentum beat both SPY buy-and-
hold (less drawdown) and pure relative momentum (better risk-
adjusted returns) over 1990-2014. The two filters work together:
relative momentum picks winners, absolute momentum avoids
holdings during secular downtrends.

Parameters to tune
------------------
  - mom_period: lookback for momentum (default 252, Antonacci uses 12-month)
  - ma_period: 200-day MA for absolute filter
  - top_n: how many stocks to hold (we run per-stock, so effectively 1)
  - rebal_period: how often to rebalance (1=every bar, 5=weekly-ish, 20=monthly)

Notes for t50
-------------
We run this per-stock (one strategy instance per symbol), so the
"top-N" part is implicit — we either hold or don't. The
"relative" part is the 12m return check vs a benchmark
(approximated as 0%, i.e. positive 12m return is the gate).
The "absolute" part is the 200d MA filter.
"""
import backtrader as bt
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy


class DualMomentumStrategy(MovingProfitStrategy):
    """
    GEMS-style dual momentum on a single stock.

    Buy when:
      - 12m return > 0 (relative momentum is positive)
      - Close > 200-day SMA (absolute momentum is positive)
    Sell when:
      - Either filter fails (we drop to cash)
    """

    NAME = "DualMomentum"

    params = (
        # Relative momentum: 12-month return
        ("mom_period", 252),

        # Absolute momentum: 200-day SMA filter
        ("ma_period", 200),

        # No take-profit (let winners run, same lesson as HPTrend)
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.12),
        ("trailing_takeprofit_pct", 0.99),
    )

    def stra_initial(self):
        # 200-day SMA for absolute filter
        self.sma = {
            d: bt.indicators.SimpleMovingAverage(d.close, period=self.p.ma_period)
            for d in self.datas
        }

    def _is_strong(self, data):
        """Dual momentum check: relative + absolute both positive."""
        if len(data) < self.p.mom_period + 1:
            return False
        # Relative momentum: 12m return > 0
        if data.close[0] <= data.close[-self.p.mom_period]:
            return False
        # Absolute momentum: close > 200-day SMA
        if data.close[0] <= self.sma[data][0]:
            return False
        return True

    def stra_buy_in(self, data):
        return self._is_strong(data)

    def stra_sell_out(self, data):
        return not self._is_strong(data)
