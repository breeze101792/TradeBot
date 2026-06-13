"""
Parabolic SAR — Welles Wilder's original trend-following indicator.

Logic
-----
  SAR is always calculated for the current period. It's a price the
  market is expected to follow. If the trend is up, SAR is below
  price and rising; if down, SAR is above price and falling.

  When price crosses SAR, the trend flips:
    - In uptrend, a close below SAR triggers SELL (and flip to downtrend)
    - In downtrend, a close above SAR triggers BUY (and flip to uptrend)

Standard parameters
-------------------
  - acceleration_factor_start: 0.02
  - acceleration_factor_max:   0.20

Why it's famous
---------------
PSAR is one of the original Wilder indicators (1978) and was
specifically designed as a trailing stop that accelerates as the
trend matures. It's the basis of many modern trailing stop systems.
"""
import backtrader as bt
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy


class ParabolicSARStrategy(MovingProfitStrategy):
    """Parabolic SAR flip-based entries, no take-profit.

    Buy when SAR flips from above to below price (uptrend).
    Sell when SAR flips from below to above price (downtrend).
    """
    NAME = "ParabolicSAR"

    params = (
        # Standard PSAR
        ("af_start", 0.02),
        ("af_max", 0.20),
        # Trailing stop / no TP
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.12),
        ("trailing_takeprofit_pct", 0.99),
    )

    def stra_initial(self):
        # Backtrader's ParabolicSAR signature: ParabolicSAR(data, period=2, af=0.02, afmax=0.20)
        # Note: there is no separate af_start; af IS the starting acceleration.
        self.psar = {d: bt.indicators.ParabolicSAR(d, period=2,
                                                    af=self.p.af_start,
                                                    afmax=self.p.af_max)
                      for d in self.datas}

    def stra_buy_in(self, data):
        if len(data) < 5:
            return False
        # PSAR below price = uptrend
        return data.close[0] > self.psar[data][0]

    def stra_sell_out(self, data):
        if len(data) < 5:
            return False
        # PSAR above price = downtrend
        return data.close[0] < self.psar[data][0]
