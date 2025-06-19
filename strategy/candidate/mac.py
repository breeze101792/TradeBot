import backtrader as bt
import pandas as pd
from math import ceil
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy

# Moving Average Crossover
class MovingAverageCrossoverStrategy(MovingProfitStrategy):
    NAME="MovingAverageCrossover"
    params = (
        # ("short_period", 5),  # Short period for moving average (5 days)
        # ("long_period", 20),  # Long period for moving average (20 days)

        # test with top50/5years 40% profit.
        ("short_period", 10),  # Short period for moving average (5 days)
        ("long_period", 20),  # Long period for moving average (20 days)

        ("risk_per_trade", MovingProfitStrategy.params.risk_per_trade),
        ("trailing_stop_pct", MovingProfitStrategy.params.trailing_stop_pct),
        ("trailing_takeprofit_pct", MovingProfitStrategy.params.trailing_takeprofit_pct),
    )

    # def __init__(self):
    #     super().__init__()
    #     print(f"after short_period: {self.params.short_period}")

    def stra_initial(self):
        self.sma_short = {data: bt.indicators.SimpleMovingAverage(data, period=self.params.short_period) for data in self.datas}
        self.sma_long = {data: bt.indicators.SimpleMovingAverage(data, period=self.params.long_period) for data in self.datas}

    def stra_buy_in(self, data):
        result = self.sma_short[data][0] > self.sma_long[data][0] and self.sma_short[data][-1] <= self.sma_long[data][-1]
        # info
        # if result:
        #     dbg_info(f"[{data.datetime.date(0)}]{data._name} {self.sma_short[data][0]:.2f}>{self.sma_long[data][0]:.2f}/{self.sma_short[data][-1]:.2f}>{self.sma_long[data][-1]:.2f}")
        return result
    def stra_sell_out(self, data):
        return self.sma_short[data][0] < self.sma_long[data][0]

class EMACrossoverStrategy(MovingProfitStrategy):
    NAME="EMACrossover"
    params = (
        # ("short_period", 5),  # Short period for moving average (5 days)
        # ("long_period", 20),  # Long period for moving average (20 days)

        # test with top50/5years 40% profit.
        ("short_period", 10),  # Short period for moving average (5 days)
        ("long_period", 20),  # Long period for moving average (20 days)

        ("risk_per_trade", MovingProfitStrategy.params.risk_per_trade),
        ("trailing_stop_pct", MovingProfitStrategy.params.trailing_stop_pct),
        ("trailing_takeprofit_pct", MovingProfitStrategy.params.trailing_takeprofit_pct),
    )

    # def __init__(self):
    #     super().__init__()
    #     print(f"after short_period: {self.params.short_period}")

    def stra_initial(self):
        self.sma_short = {data: bt.indicators.EMA(data, period=self.params.short_period) for data in self.datas}
        self.sma_long = {data: bt.indicators.EMA(data, period=self.params.long_period) for data in self.datas}

    def stra_buy_in(self, data):
        result = self.sma_short[data][0] > self.sma_long[data][0] and self.sma_short[data][-1] <= self.sma_long[data][-1]
        # info
        # if result:
        #     dbg_info(f"[{data.datetime.date(0)}]{data._name} {self.sma_short[data][0]:.2f}>{self.sma_long[data][0]:.2f}/{self.sma_short[data][-1]:.2f}>{self.sma_long[data][-1]:.2f}")
        return result
    def stra_sell_out(self, data):
        return self.sma_short[data][0] < self.sma_long[data][0]

class MACDCrossoverStrategy(MovingProfitStrategy):
    NAME="MACDCrossover"
    params = (
        # ("macd_fast", 12),  # Short period for moving average (5 days)
        # ("macd_slow", 26),  # Long period for moving average (20 days)
        # ("macd_signal", 9),  # Long period for moving average (20 days)
        ("macd_fast", 10),  # Short period for moving average (10 days)
        ("macd_slow", 20),  # Long period for moving average (20 days)
        ("macd_signal", 10),  # Long period for moving average (10 days)

        ("risk_per_trade", MovingProfitStrategy.params.risk_per_trade),
        ("trailing_stop_pct", MovingProfitStrategy.params.trailing_stop_pct),
        ("trailing_takeprofit_pct", MovingProfitStrategy.params.trailing_takeprofit_pct),
    )
    def stra_initial(self):

        self.macd = {}
        for data in self.datas:
            self.macd[data] = bt.indicators.MACD(
                data.close,
                period_me1=self.p.macd_fast,
                period_me2=self.p.macd_slow,
                period_signal=self.p.macd_signal
            )

    def stra_buy_in(self, data):
        # Buy when MACD line crosses above the signal line
        return self.macd[data].macd[0] > self.macd[data].signal[0] and \
               self.macd[data].macd[-1] <= self.macd[data].signal[-1]

    def stra_sell_out(self, data):
        # Sell when MACD line crosses below the signal line
        return self.macd[data].macd[0] < self.macd[data].signal[0]
