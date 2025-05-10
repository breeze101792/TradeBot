import backtrader as bt
import pandas as pd
from math import ceil
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy

class RelativeStrengthIndexStrategy(MovingProfitStrategy):
    NAME="RelativeStrengthIndex"
    params = (
        ('rsi_period', 14),
        ('rsi_oversold', 30),
        ('rsi_exit', 50),

        ("risk_per_trade", MovingProfitStrategy.params.risk_per_trade),
        ("trailing_stop_pct", MovingProfitStrategy.params.trailing_stop_pct),
        ("trailing_takeprofit_pct", MovingProfitStrategy.params.trailing_takeprofit_pct),
    )

    def stra_initial(self):
        # self.rsi = bt.indicators.RSI_SMA(self.data.close, period=self.params.rsi_period)
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)

    def stra_buy_in(self, data):
        if len(self) < self.params.rsi_period:
            return False
        return self.rsi[0] < self.params.rsi_oversold

    def stra_sell_out(self, data):
        if len(self) < self.params.rsi_period:
            return False
        return self.rsi[0] > self.params.rsi_exit
