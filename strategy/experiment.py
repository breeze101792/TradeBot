import backtrader as bt
import pandas as pd
from utility.debug import *
from strategy.basicstrategy import *

# Test Strategy
class MovingAverageCrossover(BasicStrategy):
    NAME="MAC"
    # params = (
    #     ("short_period", 50),  # 短期均線 (50日)
    #     ("long_period", 200),  # 長期均線 (200日)
    #     ("risk_per_trade", 0.02),  # 單筆交易最大風險 (2%)
    # )
    params = (
        ("short_period", 5),  # 短期均線 (50日)
        ("long_period", 20),  # 長期均線 (200日)
        ("risk_per_trade", 0.2),  # 單筆交易最大風險 (2%)
    )

    def __init__(self):
        self.sma_short = {data: bt.indicators.SimpleMovingAverage(data, period=self.params.short_period) for data in self.datas}
        self.sma_long = {data: bt.indicators.SimpleMovingAverage(data, period=self.params.long_period) for data in self.datas}
        self.stop_loss = {}  # 記錄止損價格
        self.take_profit = {}  # 記錄止盈價格

    def next(self):
        for data in self.datas:
            pos = self.getposition(data)
            price = data.close[0]

            # 進場：短均線上穿長均線
            if not pos and self.sma_short[data][0] > self.sma_long[data][0] and self.sma_short[data][-1] <= self.sma_long[data][-1]:
                size = self.broker.get_cash() * self.params.risk_per_trade / price
                self.buy(data=data, size=size)
                self.stop_loss[data] = price * 0.95  # 設定止損 (5%)
                self.take_profit[data] = price * 1.2  # 設定止盈 (20%)
                dbg_log(f"📈 [{self.data.datetime.date(0)}]{data._name} 買入 @ {price:.2f}, 止損: {self.stop_loss[data]:.2f}, 止盈: {self.take_profit[data]:.2f}")

            # 出場：短均線下穿長均線 或 達到止盈/止損
            elif pos:
                if self.sma_short[data][0] < self.sma_long[data][0] or price < self.stop_loss[data]:
                    self.sell(data=data, size=pos.size)
                    dbg_log(f"📉 [{self.data.datetime.date(0)}]{data._name} 止損出場 @ {price:.2f}")

                elif price > self.take_profit[data]:
                    self.sell(data=data, size=pos.size)
                    dbg_log(f"🏆 [{self.data.datetime.date(0)}]{data._name} 止盈出場 @ {price:.2f}")

class MovingAverageCrossoverEn(BasicStrategy):
    NAME = "MACE"
    
    # params = (
    #     ("short_period", 50),  # Short period for moving average (50 days)
    #     ("long_period", 200),  # Long period for moving average (200 days)
    #     ("risk_per_trade", 0.02),  # Max risk per trade (20%)
    #     ("trailing_stop_pct", 0.05),  # Trailing stop percentage (5%)
    #     ("trailing_takeprofit_pct", 0.10),  # Trailing take profit percentage (10%)
    # )
    params = (
        ("short_period", 5),  # Short period for moving average (5 days)
        ("long_period", 20),  # Long period for moving average (20 days)
        ("risk_per_trade", 0.2),  # Max risk per trade (20%)
        ("trailing_stop_pct", 0.05),  # Trailing stop percentage (5%)
        ("trailing_takeprofit_pct", 0.10),  # Trailing take profit percentage (10%)
    )

    def __init__(self):
        self.sma_short = {data: bt.indicators.SimpleMovingAverage(data, period=self.params.short_period) for data in self.datas}
        self.sma_long = {data: bt.indicators.SimpleMovingAverage(data, period=self.params.long_period) for data in self.datas}
        self.stop_loss = {}  # Record stop loss prices
        self.take_profit = {}  # Record take profit prices
        self.trailing_stop = {}  # Trailing stop loss prices
        self.trailing_takeprofit = {}  # Trailing take profit prices

    def next(self):
        for data in self.datas:
            pos = self.getposition(data)
            price = data.close[0]

            # Entry: Short MA crosses above Long MA
            if not pos and self.sma_short[data][0] > self.sma_long[data][0] and self.sma_short[data][-1] <= self.sma_long[data][-1]:
                size = self.broker.get_cash() * self.params.risk_per_trade / price
                self.buy(data=data, size=size)
                self.stop_loss[data] = price * 0.95  # Set initial stop loss (5% down)
                self.take_profit[data] = price * 1.2  # Set initial take profit (20% up)
                self.trailing_stop[data] = price * 0.95  # Set initial trailing stop loss (5% down)
                self.trailing_takeprofit[data] = price * 1.2  # Set initial trailing take profit (20% up)
                dbg_log(f"📈 [{self.data.datetime.date(0)}]{data._name} Bought @ {price:.2f}, Stop Loss: {self.stop_loss[data]:.2f}, Take Profit: {self.take_profit[data]:.2f}")

            # Exit: Short MA crosses below Long MA or hit stop loss/take profit
            elif pos:
                # Update trailing stop and take profit when the price moves in your favor
                if price > self.trailing_takeprofit[data]:
                    self.trailing_takeprofit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Adjust trailing take profit
                if price > self.trailing_stop[data]:
                    self.trailing_stop[data] = max(self.trailing_stop[data], price * (1 - self.params.trailing_stop_pct))  # Adjust trailing stop loss

                # Exit conditions
                if price < self.trailing_stop[data]:
                    self.sell(data=data, size=pos.size)
                    dbg_log(f"📉 [{self.data.datetime.date(0)}]{data._name} Trailing Stop Loss hit @ {price:.2f}")

                elif price > self.trailing_takeprofit[data]:
                    self.sell(data=data, size=pos.size)
                    dbg_log(f"🏆 [{self.data.datetime.date(0)}]{data._name} Trailing Take Profit hit @ {price:.2f}")

                elif self.sma_short[data][0] < self.sma_long[data][0] or price < self.stop_loss[data]:
                    self.sell(data=data, size=pos.size)
                    dbg_log(f"📉 [{self.data.datetime.date(0)}]{data._name} Stop Loss hit @ {price:.2f}")
            else:
                stop_loss = price * 0.95  # Set initial stop loss (5% down)
                take_profit = price * 1.2  # Set initial take profit (20% up)
                dbg_log(f"- [{self.data.datetime.date(0)}]{data._name} NONE @ {price:.2f}, Stop Loss: {stop_loss:.2f}, Take Profit: {take_profit:.2f}")


class BreakoutMomentum(bt.Strategy):
    NAME="BM"
    params = (
        ("breakout_period", 20),  # 突破區間 (20日高點)
        ("stop_loss_pct", 0.03),  # 3% 止損
        # ("take_profit_pct", 0.08),  # 8% 止盈
        ("take_profit_pct", 0.15),  # 8% 止盈
        ("risk_per_trade", 0.05),  # 風險控制 (5% 資金)
    )

    def __init__(self):
        self.highest_high = {data: bt.ind.Highest(data.high, period=self.params.breakout_period) for data in self.datas}
        self.stop_loss = {}  # 記錄止損價格
        self.take_profit = {}  # 記錄止盈價格

    def next(self):
        for data in self.datas:
            pos = self.getposition(data)
            price = data.close[0]

            # 進場：當日價格突破 N 日新高
            if not pos and price > self.highest_high[data][-1]:
                size = self.broker.get_cash() * self.params.risk_per_trade / price
                self.buy(data=data, size=size)
                self.stop_loss[data] = price * (1 - self.params.stop_loss_pct)  # 設定止損
                self.take_profit[data] = price * (1 + self.params.take_profit_pct)  # 設定止盈
                dbg_log(f"🚀 [{self.data.datetime.date(0)}]{data._name} 突破買入 @ {price:.2f}, 止損: {self.stop_loss[data]:.2f}, 止盈: {self.take_profit[data]:.2f}")

            # 出場：跌破止損 或 達到止盈
            elif pos:
                if price < self.stop_loss[data]:
                    self.sell(data=data, size=pos.size)
                    dbg_log(f"⚠️ [{self.data.datetime.date(0)}]{data._name} 止損出場 @ {price:.2f}")

                elif price > self.take_profit[data]:
                    self.sell(data=data, size=pos.size)
                    dbg_log(f"🏆 [{self.data.datetime.date(0)}]{data._name} 止盈出場 @ {price:.2f}")

class BreakoutMomentum(bt.Strategy):
    NAME="BM"
    params = (
        ("breakout_period", 20),  # 突破區間 (20日高點)
        ("stop_loss_pct", 0.03),  # 3% 止損
        # ("take_profit_pct", 0.08),  # 8% 止盈
        ("take_profit_pct", 0.15),  # 8% 止盈
        ("risk_per_trade", 0.05),  # 風險控制 (5% 資金)
    )

    def __init__(self):
        self.highest_high = {data: bt.ind.Highest(data.high, period=self.params.breakout_period) for data in self.datas}
        self.stop_loss = {}  # 記錄止損價格
        self.take_profit = {}  # 記錄止盈價格

    def next(self):
        for data in self.datas:
            pos = self.getposition(data)
            price = data.close[0]

            # 進場：當日價格突破 N 日新高
            if not pos and price > self.highest_high[data][-1]:
                size = self.broker.get_cash() * self.params.risk_per_trade / price
                self.buy(data=data, size=size)
                self.stop_loss[data] = price * (1 - self.params.stop_loss_pct)  # 設定止損
                self.take_profit[data] = price * (1 + self.params.take_profit_pct)  # 設定止盈
                dbg_log(f"🚀 [{self.data.datetime.date(0)}]{data._name} 突破買入 @ {price:.2f}, 止損: {self.stop_loss[data]:.2f}, 止盈: {self.take_profit[data]:.2f}")

            # 出場：跌破止損 或 達到止盈
            elif pos:
                if price < self.stop_loss[data]:
                    self.sell(data=data, size=pos.size)
                    dbg_log(f"⚠️ [{self.data.datetime.date(0)}]{data._name} 止損出場 @ {price:.2f}")

                elif price > self.take_profit[data]:
                    self.sell(data=data, size=pos.size)
                    dbg_log(f"🏆 [{self.data.datetime.date(0)}]{data._name} 止盈出場 @ {price:.2f}")

class BreakoutMomentumEn(bt.Strategy):
    NAME="BME"
    params = {
        "breakout_period": 20,  # 突破期間
        "trailing_stop_pct": 0.05,  # 移動止損 5%
        "trailing_takeprofit_pct": 0.1,  # 移動止盈 10%
        "risk_per_trade": 0.05  # 風險資金占比
    }

    def __init__(self):
        self.highest_high = {data: bt.ind.Highest(data.high, period=self.params.breakout_period) for data in self.datas}
        self.trailing_stop = {}
        self.trailing_takeprofit = {}

    def next(self):
        for data in self.datas:
            pos = self.getposition(data)
            price = data.close[0]

            # **開倉條件：價格創新高**
            if not pos and price > self.highest_high[data][-1]:
                size = self.broker.get_cash() * self.params.risk_per_trade / price
                self.buy(data=data, size=size)

                # 設定初始移動止損 / 移動止盈
                self.trailing_stop[data] = price * (1 - self.params.trailing_stop_pct)
                self.trailing_takeprofit[data] = price * (1 + self.params.trailing_takeprofit_pct)

            # **更新移動止損 / 移動止盈**
            elif pos:
                # 當價格上漲時，更新移動止損和止盈
                if price > self.trailing_takeprofit[data]:  
                    self.trailing_stop[data] = max(self.trailing_stop[data], price * (1 - self.params.trailing_stop_pct))
                    self.trailing_takeprofit[data] = price * (1 + self.params.trailing_takeprofit_pct)

                # **出場條件**
                if price < self.trailing_stop[data]:  # 觸發移動止損
                    self.sell(data=data, size=pos.size)
                elif price > self.trailing_takeprofit[data]:  # 觸發移動止盈
                    self.sell(data=data, size=pos.size)
