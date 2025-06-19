import backtrader as bt
import pandas as pd
from math import ceil
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy

class RelativeStrengthIndexStrategy(MovingProfitStrategy):
    NAME="RelativeStrengthIndex"
    params = (
        # ('rsi_period', 14),
        # ('rsi_oversold', 30),
        # ('rsi_exit', 50),
        ('rsi_period', 10),
        ('rsi_oversold', 35),
        ('rsi_exit', 65),

        ("risk_per_trade", MovingProfitStrategy.params.risk_per_trade),
        ("trailing_stop_pct", MovingProfitStrategy.params.trailing_stop_pct),
        ("trailing_takeprofit_pct", MovingProfitStrategy.params.trailing_takeprofit_pct),
    )

    def stra_initial(self):
        # self.rsi = bt.indicators.RSI_SMA(self.data.close, period=self.params.rsi_period)
        self.rsi = bt.indicators.RSI(self.data.close, period=self.params.rsi_period)

    def stra_buy_in(self, data):
        if len(data) < self.params.rsi_period:
            return False
        return self.rsi[0] < self.params.rsi_oversold

    def stra_sell_out(self, data):
        if len(data) < self.params.rsi_period:
            return False
        return self.rsi[0] > self.params.rsi_exit

class RSI_SMA(MovingProfitStrategy):
    NAME="RSI_SMA"
    params=(('min_RSI',35),('max_RSI',65),('max_position',10),('look_back_period',14))

    # def log(self, txt, dt=None):
    #     dt = dt or self.datas[0].datetime.date(0)
    #     print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # RSI indicator
        # self.RSI = bt.indicators.RSI_SMA(self.data.close, period=self.params.look_back_period) 
        self.RSI = {data: bt.indicators.RSI_SMA(data, period=self.params.look_back_period, safediv = True)  for data in self.datas}

    def stra_buy_in(self, data):
        if len(data) < self.params.look_back_period:
            return False
        return self.RSI[data][0] < self.params.min_RSI

    def stra_sell_out(self, data):
        if len(data) < self.params.look_back_period:
            return False
        return self.RSI[data][0] > self.params.max_RSI
    # def next(self):
    #
    #     # Buy if over sold
    #     if self.RSI < self.params.min_RSI:
    #         self.buy()
    #
    #     # Sell if over buyed
    #     if self.RSI > self.params.max_RSI:
    #         self.close()
