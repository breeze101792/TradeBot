import backtrader as bt
import yfinance as yf
import datetime
import pandas as pd
import os

# 1️⃣ 定義均線突破策略 (Moving Average Crossover)
class MovingAverageCrossover(bt.Strategy):
    params = (
        ("short_period", 50),  # 短期均線 (50日)
        ("long_period", 200),  # 長期均線 (200日)
        ("risk_per_trade", 0.02),  # 單筆交易最大風險 (2%)
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

# 2️⃣ 下載 Yahoo Finance 資料
# def get_data(symbol, start, end):
#     df = yf.download(symbol, start=start, end=end, multi_level_index=False)
#     df.index = df.index.tz_localize(None)  # 移除時區，以避免 Backtrader 時間錯誤
#     return bt.feeds.PandasData(dataname=df)

def save_to_csv(df: pd.DataFrame, filename: str, folder: str = './'):
    """
    Save a Pandas DataFrame to a CSV file in a specified folder.
    Ensures the folder exists before saving.

    :param df: The DataFrame to save.
    :param folder: The target folder where the file will be saved.
    :param filename: The name of the CSV file.
    """
    # Ensure the folder exists
    os.makedirs(folder, exist_ok=True)

    # Create the full file path
    file_path = os.path.join(folder, filename)

    # Save the DataFrame to CSV
    df.to_csv(file_path, index=True)
    print(f"DataFrame saved to {file_path}")

def load_from_csv(filename: str, date_column: str = None, folder: str = './') -> pd.DataFrame:
    """
    Load a Pandas DataFrame from a CSV file if it exists.

    :param folder: The folder where the file is located.
    :param filename: The name of the CSV file.
    :param date_column: Name of the column containing dates (if any).
    :return: The loaded DataFrame, or None if the file does not exist.
    """
    file_path = os.path.join(folder, filename)

    if not os.path.exists(file_path):
        # print(f"Error: {file_path} does not exist.")
        return None

    df = pd.read_csv(file_path)

    # If a date column is specified, convert it to datetime
    if date_column and date_column in df.columns:
        df[date_column] = pd.to_datetime(df[date_column])
        df.set_index(date_column, inplace=True)

    # print(f"DataFrame loaded from {file_path}")
    return df

def get_data(symbol, start_date, end_date):
    # 嘗試先用 pandas 測試是否能成功下載 Yahoo Finance 的台股數據
    # symbol = "2454.TW"  # Yahoo Finance 上的台股代碼
    # symbol = "8069.TWO"  # Yahoo Finance 上的台股代碼
    # start_date = "2018-01-01"
    # end_date = "2025-01-01"
    ticker_local_path = './data'
    ticker_local_file = symbol + ".csv"

    # 下載股票數據
    df = load_from_csv(ticker_local_file, 'Date', folder=ticker_local_path)
    if df is None:
        df = yf.download(symbol, start=start_date, end=end_date, multi_level_index=False)
        # df = yf.symbol(ticker).history(period="max")
        save_to_csv(df, ticker_local_file, folder=ticker_local_path)

    # 檢查數據是否成功下載
    if df.empty:
        raise ValueError("從 Yahoo Finance 下載數據失敗，請檢查股票代號或網路連線。")
    # else:
    #     print("數據下載成功！顯示前幾行數據：")
        # print(df.head())
    # return df
    return bt.feeds.PandasData(dataname=df)

# 3️⃣ 設定回測環境
def run_backtest():
    cerebro = bt.Cerebro()
    cerebro.addstrategy(MovingAverageCrossover)

    # 設定初始資金
    cerebro.broker.set_cash(100000)

    # 載入多支標的
    symbols = ["AAPL", "MSFT", "GOOG", "TSLA", "NVDA"]  # 可自行修改標的
    start_date = "2020-01-01"
    end_date = "2024-01-01"

    for symbol in symbols:
        data = get_data(symbol, start_date, end_date)
        cerebro.adddata(data, name=symbol)

    # 設定交易成本
    cerebro.broker.setcommission(commission=0.001)  # 0.1% 手續費

    # 4️⃣ 執行回測
    print("🚀 啟動回測...")
    cerebro.run()
    print("✅ 回測結束，資金餘額:", cerebro.broker.getvalue())

    # 5️⃣ 繪製績效圖
    # cerebro.plot()

# 執行回測
run_backtest()

