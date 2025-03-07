import backtrader as bt
import pandas as pd

# Test Strategy
class MovingAverageCrossover(bt.Strategy):
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
                print(f"📈 {data._name} 買入 @ {price:.2f}, 止損: {self.stop_loss[data]:.2f}, 止盈: {self.take_profit[data]:.2f}")

            # 出場：短均線下穿長均線 或 達到止盈/止損
            elif pos:
                if self.sma_short[data][0] < self.sma_long[data][0] or price < self.stop_loss[data]:
                    self.sell(data=data, size=pos.size)
                    print(f"📉 {data._name} 止損出場 @ {price:.2f}")

                elif price > self.take_profit[data]:
                    self.sell(data=data, size=pos.size)
                    print(f"🏆 {data._name} 止盈出場 @ {price:.2f}")

class BreakoutMomentum(bt.Strategy):
    params = (
        ("breakout_period", 20),  # 突破區間 (20日高點)
        ("stop_loss_pct", 0.03),  # 3% 止損
        ("take_profit_pct", 0.08),  # 8% 止盈
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
                print(f"🚀 {data._name} 突破買入 @ {price:.2f}, 止損: {self.stop_loss[data]:.2f}, 止盈: {self.take_profit[data]:.2f}")

            # 出場：跌破止損 或 達到止盈
            elif pos:
                if price < self.stop_loss[data]:
                    self.sell(data=data, size=pos.size)
                    print(f"⚠️ {data._name} 止損出場 @ {price:.2f}")

                elif price > self.take_profit[data]:
                    self.sell(data=data, size=pos.size)
                    print(f"🏆 {data._name} 止盈出場 @ {price:.2f}")
