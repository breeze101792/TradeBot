import backtrader as bt
import pandas as pd
from utility.debug import *
from strategy.basic.basicstrategy import BasicStrategy
from strategy.basic.movingprofit import MovingProfitStrategy
from strategy.indicator import *

class VWAPStrategy_Legacy(BasicStrategy):
    NAME="VWAPS"
    params = (
        ('vwap_period', 20),  # VWAP 計算週期
    )

    def __init__(self):
        super().__init__()
        # 初始化 VWAP 指標
        self.vwap = VWAP(self.data)
    
    def next(self):
        if self.data.close[0] > self.vwap[0]:
            if not self.position:
                # 當價格高於 VWAP 時，買入
                size = self.broker.get_cash() * 0.1 / self.data.close[0]
                self.buy(self.data, size=size)
                dbg_log(f"Buy signal at {self.data.close[0]:.2f}")

        elif self.data.close[0] < self.vwap[0]:
            if self.position:
                # 當價格低於 VWAP 時，賣出
                self.sell(self.data, size=self.position.size)
                dbg_log(f"Sell signal at {self.data.close[0]:.2f}")

class VolumeWeightedAveragePriceStrategy(MovingProfitStrategy):
    NAME="VolumeWeightedAveragePrice"
    params = (
        ('vwap_period', 15),  # VWAP 計算週期

        ("risk_per_trade", MovingProfitStrategy.params.risk_per_trade),
        ("trailing_stop_pct", MovingProfitStrategy.params.trailing_stop_pct),
        ("trailing_takeprofit_pct", MovingProfitStrategy.params.trailing_takeprofit_pct),
    )

    def stra_initial(self):
        self.vwap = {data: VWAP(data, period=self.params.vwap_period) for data in self.datas}

    def stra_buy_in(self, data):
        if data.close[0] > self.vwap[data][0]:
            # 當價格高於 VWAP 時，買入
            # dbg_log(f"Buy signal at {self.data.close[0]:.2f}")
            return True
        else:
            return False
    def stra_sell_out(self, data):
        if data.close[0] < self.vwap[data][0]:
            # 當價格低於 VWAP 時，賣出
            # dbg_log(f"Sell signal at {self.data.close[0]:.2f}")
            return True
        else:
            return False

class VolumeWeightedAveragePriceCrossStrategy(MovingProfitStrategy):
    NAME="VolumeWeightedAveragePriceCross"
    params = (
        ("short_period", 1),  # Short period for moving average (5 days)
        ("long_period", 20),  # Long period for moving average (20 days)

        ("risk_per_trade", MovingProfitStrategy.params.risk_per_trade),
        ("trailing_stop_pct", MovingProfitStrategy.params.trailing_stop_pct),
        ("trailing_takeprofit_pct", MovingProfitStrategy.params.trailing_takeprofit_pct),
    )

    def stra_initial(self):
        # self.vwap = {data: VWAP(data, period=self.params.vwap_period) for data in self.datas}
        # self.vwap = {data: VWAP(data, period=self.params.vwap_period) for data in self.datas}

        self.vwap_short = {data: VWAP(data, period=self.params.short_period) for data in self.datas}
        self.vwap_long = {data: VWAP(data, period=self.params.long_period) for data in self.datas}

    def stra_initial(self):
        self.vwap_short = {data: bt.indicators.SimpleMovingAverage(data, period=self.params.short_period) for data in self.datas}
        self.vwap_long = {data: bt.indicators.SimpleMovingAverage(data, period=self.params.long_period) for data in self.datas}

    # def stra_buy_in(self, data):
    #     result = self.vwap_short[data][0] > self.vwap_long[data][0] and self.vwap_short[data][-1] <= self.vwap_long[data][-1]
    #     # info
    #     # if result:
    #     #     dbg_info(f"[{data.datetime.date(0)}]{data._name} {self.vwap_short[data][0]:.2f}>{self.vwap_long[data][0]:.2f}/{self.vwap_short[data][-1]:.2f}>{self.vwap_long[data][-1]:.2f}")
    #     return result
    # def stra_sell_out(self, data):
    #     return self.vwap_short[data][0] < self.vwap_long[data][0]

    def stra_buy_in(self, data):
        if self.vwap_short[data][0] > self.vwap_long[data][0]:
            # 當價格高於 VWAP 時，買入
            # dbg_log(f"Buy signal at {self.data.close[0]:.2f}")
            return True
        else:
            return False
    def stra_sell_out(self, data):
        if self.vwap_short[data][0] < self.vwap_long[data][0]:
            # 當價格低於 VWAP 時，賣出
            # dbg_log(f"Sell signal at {self.data.close[0]:.2f}")
            return True
        else:
            return False
