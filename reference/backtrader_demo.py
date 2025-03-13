import backtrader as bt
import yfinance as yf
import pandas as pd
from datetime import datetime
import os
import traceback

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

def get_ticker_from_yfinance(ticker):
    # 嘗試先用 pandas 測試是否能成功下載 Yahoo Finance 的台股數據
    # ticker = "2454.TW"  # Yahoo Finance 上的台股代碼
    # ticker = "8069.TWO"  # Yahoo Finance 上的台股代碼
    # start_date = "2018-01-01"
    # end_date = "2025-01-01"
    ticker_local_path = './data'
    ticker_local_file = ticker + ".csv"

    # 下載股票數據
    df = load_from_csv(ticker_local_file, 'Date', folder=ticker_local_path)
    if df is None:
        # df = yf.download(ticker, start=start_date, end=end_date, multi_level_index=False)
        df = yf.Ticker(ticker).history(period="max")
        save_to_csv(df, ticker_local_file, folder=ticker_local_path)

    # 檢查數據是否成功下載
    if df.empty:
        raise ValueError("從 Yahoo Finance 下載數據失敗，請檢查股票代號或網路連線。")
    # else:
    #     print("數據下載成功！顯示前幾行數據：")
    #     print(df.head())
    return df

################################################################################
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
            # print(f"Date: {self.data.datetime.date(0)} Buy, SMA50: {self.sma1[0]:.2f}, SMA200: {self.sma2[0]:.2f}, RSI: {self.rsi[0]:.2f}")
        elif self.sma1[0] < self.sma2[0] and self.position:
            self.sell()
            # print(f"Date: {self.data.datetime.date(0)} Sell, SMA50: {self.sma1[0]:.2f}, SMA200: {self.sma2[0]:.2f}, RSI: {self.rsi[0]:.2f}")


class TurtleTrading(bt.Strategy):
    params = dict(
        entry_period=20,
        exit_period=10,
        stop_loss=0.05,
        take_profit=0.15
    )

    def __init__(self):
        self.highest = bt.indicators.Highest(self.data.high, period=self.params.entry_period)
        self.lowest = bt.indicators.Lowest(self.data.low, period=self.params.exit_period)
        self.entry_price = None

    def next(self):
        if not self.position:
            if self.data.close[0] > self.highest[-1]:
                self.buy()
                self.entry_price = self.data.close[0]

        else:
            if self.data.close[0] < self.lowest[-1]:
                self.sell()
            elif self.data.close[0] >= self.entry_price * (1 + self.params.take_profit):
                self.sell()
            elif self.data.close[0] <= self.entry_price * (1 - self.params.stop_loss):
                self.sell()

class RSIWithMA(bt.Strategy):
    params = dict(
        rsi_period=14,
        ma_period=200,
        stop_loss=0.03,
        take_profit=0.06
    )

    def __init__(self):
        self.rsi = bt.indicators.RSI(period=self.params.rsi_period)
        self.sma = bt.indicators.SMA(period=self.params.ma_period)
        self.entry_price = None

    def next(self):
        if not self.position:
            if self.rsi[0] < 30 and self.data.close[0] > self.sma[0]:
                self.buy()
                self.entry_price = self.data.close[0]

        else:
            if self.rsi[0] > 70:
                self.sell()
            elif self.data.close[0] >= self.entry_price * (1 + self.params.take_profit):
                self.sell()
            elif self.data.close[0] <= self.entry_price * (1 - self.params.stop_loss):
                self.sell()

################################################################################
def main():
    init_crash = 1000000
    total_earn = 0
    # ticker = "0050.TW"  # Yahoo Finance 上的台股代碼
    ticker_list = ["0050.TW", "2454.TW", "8069.TWO", "6533.TW", "2412.TW", "2379.TW"]
    strategy_list = [TestStrategy, TurtleTrading, RSIWithMA]

    for each_strategy in strategy_list:
        print(f"Straegy Testing : {each_strategy}")
        print(f"===========================================")
        for each_ticker in ticker_list:
            try:
                ticker = each_ticker

                # print(f"Starting Testing : {each_ticker}")
                # print(f"Starting Testing : {each_ticker}")
                # print(f"===========================================")
                # ticker = "2454.TW"  # Yahoo Finance 上的台股代碼
                # ticker = "8069.TWO"  # Yahoo Finance 上的台股代碼
                df = get_ticker_from_yfinance(ticker)
                # 初始化 Backtrader
                cerebro = bt.Cerebro()

                # 把 Yahoo Finance 下載的 pandas DataFrame 轉換成 Backtrader DataFeed
                data = bt.feeds.PandasData(dataname=df)
                # 加載數據到回測引擎
                cerebro.adddata(data)
                # 加載策略
                cerebro.addstrategy(each_strategy)
                # 設定初始資金
                cerebro.broker.set_cash(init_crash)
                # 設定手續費
                cerebro.broker.setcommission(commission=0.001)
                # 設定滑點
                cerebro.broker.set_slippage_perc(perc=0.001)
                # 顯示初始資金
                # print(f"Starting Portfolio Value: {cerebro.broker.getvalue()}")
                # 運行回測
                cerebro.run()
                # 顯示最終資金
                # print(f"Ending   Portfolio Value: {cerebro.broker.getvalue()}")

                profit = (cerebro.broker.getvalue() - init_crash)/init_crash * 100
                print(f"Profit {each_ticker}: {(cerebro.broker.getvalue() - init_crash)}/{profit:.2f}%")
                # 繪製回測圖表
                # cerebro.plot()
                total_earn += cerebro.broker.getvalue() - init_crash
            except Exception as e:
                print(e)

                traceback_output = traceback.format_exc()
                print(traceback_output)
            finally:
                pass
        print(f"Final Portfolio Value: {total_earn}\n")


if __name__ == "__main__":
    main()
