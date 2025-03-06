import backtrader as bt
import yfinance as yf
import pandas as pd
from datetime import datetime

# 嘗試先用 pandas 測試是否能成功下載 Yahoo Finance 的台股數據
# ticker = "2454.TW"  # Yahoo Finance 上的台股代碼
ticker = "8069.TWO"  # Yahoo Finance 上的台股代碼
start_date = "2018-01-01"
end_date = "2025-01-01"

# 下載股票數據
df = yf.download(ticker, start=start_date, end=end_date, multi_level_index=False)

# 檢查數據是否成功下載
if df.empty:
    raise ValueError("從 Yahoo Finance 下載數據失敗，請檢查股票代號或網路連線。")
else:
    print("數據下載成功！顯示前幾行數據：")
    print(df.head())

# 創建 Backtrader 策略
class TestStrategy(bt.Strategy):
    params = (('sma1', 50), ('sma2', 200), ('rsi', 14))

    def __init__(self):
        self.sma1 = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.sma1)
        self.sma2 = bt.indicators.SimpleMovingAverage(self.data.close, period=self.params.sma2)
        self.rsi = bt.indicators.RelativeStrengthIndex(period=self.params.rsi)

    def next(self):

        if self.sma1[0] > self.sma2[0] and not self.position:
            self.buy()
            print(f"Date: {self.data.datetime.date(0)} Buy, SMA50: {self.sma1[0]:.2f}, SMA200: {self.sma2[0]:.2f}, RSI: {self.rsi[0]:.2f}")
        elif self.sma1[0] < self.sma2[0] and self.position:
            self.sell()
            print(f"Date: {self.data.datetime.date(0)} Sell, SMA50: {self.sma1[0]:.2f}, SMA200: {self.sma2[0]:.2f}, RSI: {self.rsi[0]:.2f}")

# 初始化 Backtrader
cerebro = bt.Cerebro()

# 把 Yahoo Finance 下載的 pandas DataFrame 轉換成 Backtrader DataFeed
data = bt.feeds.PandasData(dataname=df)

# 加載數據到回測引擎
cerebro.adddata(data)

# 加載策略
cerebro.addstrategy(TestStrategy)

# 設定初始資金
cerebro.broker.set_cash(1000000)

# 設定手續費
cerebro.broker.setcommission(commission=0.001)

# 設定滑點
cerebro.broker.set_slippage_perc(perc=0.001)

# 顯示初始資金
print(f"Starting Portfolio Value: {cerebro.broker.getvalue()}")

# 運行回測
cerebro.run()

# 顯示最終資金
print(f"Ending Portfolio Value: {cerebro.broker.getvalue()}")

# 繪製回測圖表
# cerebro.plot()

