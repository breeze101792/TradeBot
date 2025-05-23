import backtrader as bt
import pandas as pd
from utility.debug import *
from strategy.basic.basicstrategy import *
from strategy.basic.movingprofit import MovingProfitStrategy

class Test2Strategy(MovingProfitStrategy):
    NAME="Test2"
    params = dict(
        bb_period=20, bb_stddev=2,
        rsi_period=14, rsi_entry=55,
        macd_fast=12, macd_slow=26, macd_signal=9,
        vol_period=20,
        trail_percent=0.05,  # 移動止盈距離 (5%)
        max_loss=0.05,       # 最大單筆虧損5%
        max_add=1            # 最大加碼次數
    )

    def stra_initial(self):
        self.bb = bt.indicators.BollingerBands(
            self.data.close, period=self.p.bb_period, devfactor=self.p.bb_stddev)
        self.rsi = bt.indicators.RSI(
            self.data.close, period=self.p.rsi_period)
        self.macd = bt.indicators.MACD(
            self.data.close, period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal)
        self.vol_ma = bt.indicators.SMA(self.data.volume, period=self.p.vol_period)

    def stra_sell_out(self, data):
        if (self.data.close[0] > self.bb.top[0] and
            self.rsi[0] > self.p.rsi_entry and
            self.macd.macd[0] > self.macd.signal[0] and
            self.data.volume[0] > self.vol_ma[0]):
            return True
        else:
            return False

    def stra_buy_in(self, data):
        if (self.rsi[0] < 50 or
            self.macd.macd[0] < self.macd.signal[0] or
            self.data.close[0] < self.bb.mid[0]):
            return True
        else:
            return False


class TestStrategy_back(BasicStrategy):
    NAME="Test"
    params = dict(
        bb_period=20, bb_stddev=2,
        rsi_period=14, rsi_entry=55,
        macd_fast=12, macd_slow=26, macd_signal=9,
        vol_period=20,
        trail_percent=0.05,  # 移動止盈距離 (5%)
        max_loss=0.05,       # 最大單筆虧損5%
        max_add=1            # 最大加碼次數
    )

    def __init__(self):
        self.bb = bt.indicators.BollingerBands(
            self.data.close, period=self.p.bb_period, devfactor=self.p.bb_stddev)
        self.rsi = bt.indicators.RSI(
            self.data.close, period=self.p.rsi_period)
        self.macd = bt.indicators.MACD(
            self.data.close, period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal)
        self.vol_ma = bt.indicators.SMA(self.data.volume, period=self.p.vol_period)

        self.order = None
        self.buyprice = None
        self.add_count = 0

        # 計算勝率用
        # self.total_trades = 0
        # self.win_trades = 0

    def next(self):
        if self.order:
            return  # 如果有未完成訂單則不執行任何動作

        if not self.position:
            # 多頭進場條件
            if (self.data.close[0] > self.bb.top[0] and
                self.rsi[0] > self.p.rsi_entry and
                self.macd.macd[0] > self.macd.signal[0] and
                self.data.volume[0] > self.vol_ma[0]):

                self.order = self.buy()
                self.buyprice = self.data.close[0]
                self.add_count = 0
                # 設定初始停損單 (最大虧損5%)
                self.sell(exectype=bt.Order.Stop,
                          price=self.buyprice*(1 - self.p.max_loss))

        else:
            # 加碼條件 (最大2次)
            # if self.add_count < self.p.max_add:
            #     if (self.data.close[0] > self.bb.top[0] and
            #         self.rsi[0] > self.p.rsi_entry and
            #         self.macd.macd[0] > self.macd.signal[0] and
            #         self.data.volume[0] > self.vol_ma[0]):
            #
            #         self.order = self.buy()
            #         self.add_count += 1
            #         # 更新停損單為整體部位成本價5%下方
            #         new_stop_price = self.position.price * (1 - self.p.max_loss)
            #         self.sell(exectype=bt.Order.Stop, price=new_stop_price, oco=self.order)

            # 出場條件（RSI或MACD轉弱或跌破布林中線）
            if (self.rsi[0] < 50 or
                self.macd.macd[0] < self.macd.signal[0] or
                self.data.close[0] < self.bb.mid[0]):
                self.order = self.close()

            # 移動止盈 (價格持續創新高時)
            elif self.data.close[0] > self.buyprice * (1 + self.p.trail_percent):
                trail_stop_price = self.data.close[0] * (1 - self.p.trail_percent)
                self.sell(exectype=bt.Order.Stop, price=trail_stop_price)

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                print(f"買進 @ {order.executed.price:.2f}")
            elif order.issell():
                print(f"賣出 @ {order.executed.price:.2f}")
                self.total_trades += 1
                profit = order.executed.price - self.buyprice
                if profit > 0:
                    self.win_trades += 1

            self.order = None

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print('訂單取消或被拒絕')
            self.order = None

    # def stop(self):
    #     if self.total_trades > 0:
    #         win_rate = (self.win_trades / self.total_trades) * 100
    #         print(f"策略總交易數: {self.total_trades}")
    #         print(f"獲利交易數: {self.win_trades}")
    #         print(f"策略勝率: {win_rate:.2f}%")
    #     else:
    #         print("無交易發生，無法計算勝率。")

