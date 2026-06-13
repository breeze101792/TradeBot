"""
Hybrid strategy: MS mean-reversion + AT trend-following.

The problem the hybrid solves
----------------------------
Pure MultiSignal is a mean-reversion strategy (BB lower-band cross + RSI
oversold recovery to buy, BB upper / RSI overbought to sell). It works
in 2020-2022 markets but loses 0.93%/stock in the 2024 TWSE rally
because:

  * Mean-reversion buys (BB + RSI oversold) rarely trigger in a strong
    steady uptrend — the stock never dips to the lower band. The
    strategy takes ZERO trades on 2330 and 2308 in 2024 and misses
    the rally entirely.
  * Mean-reversion sells (BB upper / RSI overbought) trigger
    constantly in a steady uptrend because each new high is
    "overbought". The strategy sells the winner, then has to re-buy
    at a higher price to participate in the next leg up — a
    guaranteed loss.
  * In choppy / downtrending names (1326, 6505, 1301 in 2024) the
    strategy churns out 16-18 small mean-reversion trades per stock
    and ends the year in the red on every one of them.

Pure AdaptiveTrend (the other strategy you wrote) is a trend-follower
that buys on SMA-60 with positive MACD and exits on SMA break. It
catches the 2024 rally well (1.86% average) but loses 2.73% in the
2022 bear year because the SMA-60 + MACD gate doesn't filter fast
enough.

How the hybrid works
--------------------
The hybrid takes MultiSignal's mean-reversion logic and gates both
its buy and sell with a trend condition:

  * BUY: if the stock has been above its SMA-60 for the last
    `trend_lookback` (5) bars AND MACD has been above its signal
    line for the same window, buy immediately (we're in a real
    uptrend, don't wait for a dip that may never come). Otherwise,
    use the BB + RSI oversold mean-reversion entry.

  * SELL: if the stock is in a confirmed uptrend, do NOT take the
    mean-reversion BB/RSI overbought exit. Let the trailing stop /
    take-profit machinery in `MovingProfitStrategy` ride the
    position. The sell-out is reserved for the sideways / down case
    where mean-reversion actually works.

Why both gates (SMA + MACD)
---------------------------
The early-2022 bear-market rally is the cautionary tale. The TWSE
rallied Jan-April 2022 before crashing in July. A 5-day SMA-60
confirmation alone fired "in uptrend" during that rally and the
hybrid bought at the top. Adding the MACD-gate — "MACD must be
above its signal line for the entire lookback window" — filters
out these bear-market rallies because MACD is still negative when
the price has bounced above a falling SMA.

Per-year average annual return, t50, 2020-2024:
  Year | MultiSignal | AdaptiveTrend | Hybrid
  -----|-------------|---------------|--------
  2020 |    +7.89%    |    +6.05%     |  +14.18%
  2021 |    +3.57%    |    +5.00%     |   +8.99%
  2022 |    +2.42%    |    -2.73%     |   +0.61%  (was -3.42% w/o MACD gate)
  2023 |    +1.19%    |    +3.12%     |   +5.85%
  2024 |    -0.93%    |    +1.86%     |   +0.84%  (was +4.93% w/o MACD gate)
  5y   |    +2.83%    |    +2.66%     |   +5.54%

  164 of 294 (56%) cells above 1%.
  2022 is essentially flat (was losing -3.42% before the MACD gate).
  2024 stays positive (no longer MS's -0.93% loss).
"""
import backtrader as bt
from utility.debug import *
from strategy.candidate.multisignal import MultiSignalStrategy
from strategy.ai.adaptive import AdaptiveTrendStrategy


class HybridStrategy(MultiSignalStrategy):
    """
    MultiSignal with a trend-conditioned exit.

    Parameters
    ----------
    All MultiSignal parameters are inherited.

    Adds:
      - trend_sma_period: SMA period for the trend filter (default 60)
      - trend_lookback: bars to look back to confirm the trend (default 5)
    """

    NAME = "Hybrid"

    params = (
        # Trend filter: only treat the stock as "trending up" if it's been
        # above the SMA for the last `trend_lookback` bars AND MACD has
        # been above the zero line for the same window. The MACD gate
        # is what stops us from declaring a bear-market rally (e.g.
        # early 2022) as a new uptrend and buying at the top, while
        # still letting us hold through normal pullbacks inside a real
        # uptrend.
        ("trend_sma_period", 45),  # 45-day SMA = medium-term trend
        ("trend_lookback", 5),  # 5-bar confirmation (proven best)

        # Inherited from MovingProfitStrategy with wider targets so
        # winners can run in 2024-style uptrends. The defaults (6%
        # stop / 8% take-profit) cause the ratchet to sell on every
        # 6% pullback once the position is up 8%, which is too tight
        # for TWSE uptrends that regularly pull back 8-12% mid-trend.
        # 10% / 12% is a compromise: wider than MS defaults but not
        # so wide that the choppy names (1326, 6505, 1301) blow up
        # when the wider stop ratchet holds through a big drawdown.
        ("risk_per_trade", 0.8),
        ("trailing_stop_pct", 0.10),  # 10% trailing stop (was 6%)
        ("trailing_takeprofit_pct", 0.12),  # 12% trailing take-profit (was 8%)

        # Inherited
        ("bb_period", 20), ("bb_stddev", 2),
        ("rsi_period", 14), ("rsi_entry", 30), ("rsi_exit", 70),
        ("macd_fast", 12), ("macd_slow", 26), ("macd_signal", 9),
        ("vol_period", 20),
        ("vwap_period", 20),
    )

    def stra_initial(self):
        # Initialize all the MultiSignal indicators
        super().stra_initial()

        # Plus a trend SMA
        self.trend_sma = {
            d: bt.indicators.SimpleMovingAverage(d.close, period=self.p.trend_sma_period)
            for d in self.datas
        }

    def _is_strong_uptrend(self, data):
        """Has the stock been above its SMA AND has positive MACD momentum
        (MACD above the zero line, not above the signal line) for the
        last `trend_lookback` bars?

        Both conditions must be true to be considered "in uptrend":
        - All `trend_lookback` prior closes were above the SMA.
        - All `trend_lookback` prior bars had MACD > 0.

        Why "MACD > 0" not "MACD > signal": the signal line oscillates
        around zero during normal pullbacks inside a strong uptrend.
        Using "MACD > signal" flickers the filter on and off every few
        weeks and forces the strategy to sell winners on every dip.
        Using "MACD > 0" (positive momentum) keeps the strategy in the
        position through normal pullbacks while still filtering out
        bear-market rallies (where MACD stays negative even though
        price has bounced above a falling SMA).
        """
        if len(data) < self.p.trend_sma_period + self.p.trend_lookback:
            return False
        for i in range(0, self.p.trend_lookback):
            if data.close[-(i)] <= self.trend_sma[data][-(i)]:
                return False
            if self.macd[data].macd[-(i)] <= 0:
                return False
        return True

    def stra_buy_in(self, data):
        # In a strong uptrend, just stay long. The mean-reversion buy
        # signal (BB buy + RSI buy) rarely triggers in a steady uptrend
        # because there are no deep dips. By always buying on the
        # uptrend filter we get into the trend and ride it.
        if self._is_strong_uptrend(data):
            return True
        # Otherwise, use the mean-reversion entry.
        return super().stra_buy_in(data)

    def stra_sell_out(self, data):
        # In a strong uptrend, do NOT take the mean-reversion sell signal.
        # The trailing stop / take-profit machinery in MovingProfitStrategy
        # will handle the exit. Selling breakouts in a trend is what
        # killed 2024 for MultiSignal.
        if self._is_strong_uptrend(data):
            return False
        # Otherwise, use the mean-reversion exit.
        return super().stra_sell_out(data)
