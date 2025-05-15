import backtrader as bt
import pandas as pd
from utility.debug import *
from strategy.basic.basicstrategy import BasicStrategy
from strategy.indicator import *

# default strategy
ExitStrategy = BasicStrategy

class PriceVolumeStrategy(ExitStrategy):
    NAME="PVS"
    params = (
        ('short_period', 5),
        ('long_period', 20),
    )

    def __init__(self):
        super().__init__()
        self.sma_short = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.short_period)
        self.sma_long = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.long_period)

    def next(self):
        if self.sma_short[0] > self.sma_long[0] and self.data.close[0] > self.data.open[0] and self.data.volume[0] > self.data.volume[-1]:
            if not self.position:
                size = self.broker.get_cash() * 0.1 / self.data.close[0]
                self.buy(self.data, size=size)
                dbg_log(f"Buy signal: {self.data.close[0]:.2f}")
        elif self.sma_short[0] < self.sma_long[0] and self.data.close[0] < self.data.open[0] and self.data.volume[0] > self.data.volume[-1]:
            if self.position:
                self.sell(self.data, size=self.position.size)
                dbg_log(f"Sell signal: {self.data.close[0]:.2f}")


class OBVStrategy(ExitStrategy):
    NAME="OBVS"
    params = (
        ('obv_period', 14),  # OBV 計算週期
    )

    def __init__(self):
        super().__init__()
        # 初始化 OBV 指標
        self.obv = OnBalanceVolume(self.data)
        self.crossover = bt.indicators.CrossOver(self.data.close, self.obv)

    def next(self):
        if self.crossover > 0:
            if not self.position:
                # 當 OBV 穿越價格線向上時，買入
                size = self.broker.get_cash() * 0.1 / self.data.close[0]  # 風險控制為 10% 的現金
                self.buy(data, size=size)
                dbg_log(f"Buy signal at {self.data.close[0]:.2f}")
        
        elif self.crossover < 0:
            if self.position:
                # 當 OBV 穿越價格線向下時，賣出
                self.sell(data, size=self.position.size)
                dbg_log(f"Sell signal at {self.data.close[0]:.2f}")


class ADLineStrategy(ExitStrategy):
    NAME="ADLS"
    params = (
        ('ad_period', 14),  # A/D 線計算週期
    )

    def __init__(self):
        super().__init__()
        # 初始化 A/D 線
        self.ad_line = AccumulationDistribution(self.data)
        self.crossover = bt.indicators.CrossOver(self.data.close, self.ad_line)

    def next(self):
        if self.crossover > 0:
            if not self.position:
                # 當 A/D 線上穿價格線時，買入
                size = self.broker.get_cash() * 0.1 / self.data.close[0]  # 風險控制為 10% 的現金
                self.buy(data, size=size)
                dbg_log(f"Buy signal at {self.data.close[0]:.2f}")
        
        elif self.crossover < 0:
            if self.position:
                # 當 A/D 線下穿價格線時，賣出
                self.sell(size=self.position.size)
                dbg_log(f"Sell signal at {self.data.close[0]:.2f}")


class VWAPStrategy(ExitStrategy):
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

class PriceVolumeBreakoutStrategy(ExitStrategy):
    NAME="PVBS"
    params = (
        ('breakout_threshold', 1.5),  # 當成交量超過平均量的 1.5 倍時，視為突破
    )

    def __init__(self):
        super().__init__()
        self.highest_close = bt.indicators.Highest(self.data.close, period=20)  # 最高價格
        self.lowest_close = bt.indicators.Lowest(self.data.close, period=20)    # 最低價格
        self.avg_volume = bt.indicators.SimpleMovingAverage(self.data.volume, period=20)  # 平均成交量

    def next(self):
        # 成交量劇增，且價格突破最高/最低區間
        if self.data.close[0] > self.highest_close[0] and self.data.volume[0] > self.avg_volume[0] * self.params.breakout_threshold:
            if not self.position:
                # 當價格突破區間並且成交量劇增時，買入
                size = self.broker.get_cash() * 0.1 / self.data.close[0]
                self.buy(self.data, size=size)
                dbg_log(f"Breakout Buy signal at {self.data.close[0]:.2f}")

        elif self.data.close[0] < self.lowest_close[0] and self.data.volume[0] > self.avg_volume[0] * self.params.breakout_threshold:
            if self.position:
                # 當價格突破最低區間並且成交量劇增時，賣出
                self.sell(self.data, size=self.position.size)
                dbg_log(f"Breakout Sell signal at {self.data.close[0]:.2f}")

class CMFStrategy(ExitStrategy):
    NAME="CMFS"
    params = (
        ('cmf_period', 20),  # CMF 計算週期
    )

    def __init__(self):
        super().__init__()
        # 初始化 CMF 指標
        self.cmf = ChaikinMoneyFlow(self.data, period=self.params.cmf_period)
    
    def next(self):
        if self.cmf[0] > 0:
            if not self.position:
                # 當 CMF 大於 0 時，表示資金流入，買入
                size = self.broker.get_cash() * 0.1 / self.data.close[0]
                self.buy(self.data, size=size)
                dbg_log(f"Buy signal at {self.data.close[0]:.2f}")

        elif self.cmf[0] < 0:
            if self.position:
                # 當 CMF 小於 0 時，表示資金流出，賣出
                self.sell(self.data, size=self.position.size)
                dbg_log(f"Sell signal at {self.data.close[0]:.2f}")

class VolumeSpikeStrategy(ExitStrategy):
    NAME="VSS"
    params = (
        ('volume_spike_factor', 2),  # 成交量是過去平均量的幾倍才算劇增
        ('period', 20),  # 計算平均成交量的週期
    )

    def __init__(self):
        super().__init__()
        self.avg_volume = bt.indicators.SimpleMovingAverage(self.data.volume, period=self.params.period)

    def next(self):
        if self.data.volume[0] > self.avg_volume[0] * self.params.volume_spike_factor:
            if self.data.close[0] > self.data.open[0]:
                if not self.position:
                    size = self.broker.get_cash() * 0.1 / self.data.close[0]
                    self.buy(self.data, size=size)
                    dbg_log(f"Volume spike Buy signal at {self.data.close[0]:.2f}")
            elif self.data.close[0] < self.data.open[0]:
                if self.position:
                    self.sell(self.data, size=self.position.size)
                    dbg_log(f"Volume spike Sell signal at {self.data.close[0]:.2f}")


