
import backtrader as bt
import pandas as pd
from math import ceil
from utility.debug import *
from strategy.basic.movingprofit import MovingProfitStrategy

class BollingerMeanReversionStrategy(MovingProfitStrategy):
    NAME="BollingerMeanReversion"
    params = (
        ('bb_period', 20),        # 布林帶週期
        ('bb_devfactor', 2),      # 標準差倍數

        ("risk_per_trade", MovingProfitStrategy.params.risk_per_trade),
        ("trailing_stop_pct", MovingProfitStrategy.params.trailing_stop_pct),
        ("trailing_takeprofit_pct", MovingProfitStrategy.params.trailing_takeprofit_pct),
    )

    def stra_initial(self):
        self.bb = bt.indicators.BollingerBands(
            self.data.close,
            period=self.params.bb_period,
            devfactor=self.params.bb_devfactor
        )

    def stra_buy_in(self, data):
        if len(self) < self.params.bb_period:
            return  False
        return self.data.close[0] <= self.bb.lines.bot[0]

    def stra_sell_out(self, data):
        if len(self) < self.params.bb_period:
            return  False
        return self.data.close[0] >= self.bb.lines.mid[0]
