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
        return self.sma_short[data][0] > self.sma_long[data][0] and self.sma_short[data][-1] <= self.sma_long[data][-1]
    def stra_sell_out(self, data):
        return self.sma_short[data][0] < self.sma_long[data][0]
