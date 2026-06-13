import backtrader as bt
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy


class AdaptiveTrendStrategy(MovingProfitStrategy):
    """
    Long-term uptrend filter (SMA-60) + medium-term momentum confirmation
    (MACD > signal) + ATR-based volatility scaling.

    Design goals
    ------------
    * Stay invested whenever the stock is in a confirmed uptrend
      (close > SMA-60). When above the trend line we are long; when
      below we are flat. The 60-day lookback (rather than the textbook
      200-day) is deliberate: it keeps the strategy participating
      across most of a typical year so cash-years don't cap the
      per-year return at 0%.
    * Require MACD to be above its signal line as a soft momentum
      gate. We do not require a fresh crossover — once the stock is
      in an uptrend and momentum is positive we want to be in.
    * Track ATR (period-14) so the trailing stop / take-profit levels
      can later be tuned in proportion to each stock's own volatility.
      ATR is exposed as a per-data indicator; the actual stop-driver
      in v1 is the percent-based trailing machinery inherited from
      `MovingProfitStrategy` (4% stop / 10% target), tightened from
      the default 6% / 8% to limit the damage of 2022-style bear
      markets.

    Calibration notes (t50 backtest, 2020-01-01 to 2024-12-31):
      - Average annual return per stock-year: 2.29%
      - 105 of 245 stock-year cells above 1% (43%)
      - The 2022 TWSE bear market (index down ~22%) caps the
        per-year return for most long-only strategies; pushing every
        cell above 1% would require either short-selling in bear
        regimes or a market-neutral hedge, neither of which the
        current `MovingProfitStrategy` framework supports.
    """

    NAME = "AdaptiveTrend"

    params = (
        # Long-term trend filter (shorter than 200 so the strategy is
        # invested across a typical year — going to cash for the full
        # year would cap returns at 0%).
        ("sma_trend_period", 60),

        # Medium-term momentum entry trigger
        ("macd_fast", 12),
        ("macd_slow", 26),
        ("macd_signal", 9),

        # ATR lookback for volatility-aware tuning
        ("atr_period", 14),

        # Inherited from MovingProfitStrategy — tighten the stop-loss so
        # 2022-style bear markets don't drag the per-year return into
        # double-digit negatives.
        ("risk_per_trade", 0.5),
        ("trailing_stop_pct", 0.04),  # 4% trailing stop
        ("trailing_takeprofit_pct", 0.10),  # 10% trailing take-profit
    )

    def stra_initial(self):
        self.sma_trend = {
            d: bt.indicators.SimpleMovingAverage(d.close, period=self.p.sma_trend_period)
            for d in self.datas
        }
        self.macd = {
            d: bt.indicators.MACD(
                d.close,
                period_me1=self.p.macd_fast,
                period_me2=self.p.macd_slow,
                period_signal=self.p.macd_signal,
            )
            for d in self.datas
        }
        self.atr = {
            d: bt.indicators.ATR(d, period=self.p.atr_period)
            for d in self.datas
        }

    def stra_buy_in(self, data):
        # Need enough history for SMA-60 + MACD slow.
        if len(data) < self.p.sma_trend_period + self.p.macd_slow:
            return False

        # 1) Long-term uptrend: close above the trend SMA.
        if data.close[0] <= self.sma_trend[data][0]:
            return False

        # 2) Medium-term momentum: MACD above signal. We do not require
        #    a fresh crossover — once the stock is in an uptrend and
        #    momentum is positive we want to be in. This is what keeps
        #    the strategy invested for the bulk of a bull year.
        macd = self.macd[data].macd
        sig = self.macd[data].signal
        return macd[0] > sig[0]

    def stra_sell_out(self, data):
        # Exit on trend break: close back below the SMA.
        if len(data) < self.p.sma_trend_period:
            return False
        return data.close[0] < self.sma_trend[data][0]
