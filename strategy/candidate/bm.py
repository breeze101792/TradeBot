
import backtrader as bt
import pandas as pd
from math import ceil
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy

# Moving Average Crossover
class BreakoutMomentumStrategy(MovingProfitStrategy):
    NAME="BreakoutMomentum"
    params = (
        # ("breakout_period", 20),  # 突破區間 (20日高點)
        ("breakout_period", 15),  # 突破區間 (15日高點)

        ("risk_per_trade", MovingProfitStrategy.params.risk_per_trade),
        ("trailing_stop_pct", MovingProfitStrategy.params.trailing_stop_pct),
        ("trailing_takeprofit_pct", MovingProfitStrategy.params.trailing_takeprofit_pct),
    )

    def stra_initial(self):
        self.highest_high = {data: bt.ind.Highest(data.high, period=self.params.breakout_period) for data in self.datas}
        self.vol_short = {data: bt.indicators.SimpleMovingAverage(self.data.volume, period=self.params.breakout_period) for data in self.datas}

    def stra_buy_in(self, data):
        # we only intrest the popular product.
        if self.vol_short[data][0] < 100:
            return False
        price = data.close[0]
        return price > self.highest_high[data][-1]

    def stra_sell_out(self, data):
        # not exist strategy. use stop_loss to exit.
        return False
