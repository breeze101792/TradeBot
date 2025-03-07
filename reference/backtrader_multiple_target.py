import backtrader as bt
import yfinance as yf
import datetime

import pandas as pd
import os

# 1️⃣ 定義策略
class BreakoutMomentum(bt.Strategy):
    params = (("breakout_period", 20), ("stop_loss_pct", 0.03), ("take_profit_pct", 0.08), ("risk_per_trade", 0.05))

    def __init__(self):
        self.highest_high = {data: bt.ind.Highest(data.high, period=self.params.breakout_period) for data in self.datas}
        self.stop_loss = {}
        self.take_profit = {}

    def next(self):
        for data in self.datas:
            pos = self.getposition(data)
            price = data.close[0]

            if not pos and price > self.highest_high[data][-1]:
                size = self.broker.get_cash() * self.params.risk_per_trade / price
                self.buy(data=data, size=size)
                self.stop_loss[data] = price * (1 - self.params.stop_loss_pct)
                self.take_profit[data] = price * (1 + self.params.take_profit_pct)

            elif pos:
                if price < self.stop_loss[data]:
                    self.sell(data=data, size=pos.size)
                elif price > self.take_profit[data]:
                    self.sell(data=data, size=pos.size)

# 2️⃣ 下載 Yahoo Finance 資料
# def get_data(symbol, start, end):
#     df = yf.download(symbol, start=start, end=end)
#     df.index = df.index.tz_localize(None)
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
    cerebro.addstrategy(BreakoutMomentum)

    cerebro.broker.set_cash(100000)

    symbols = ["TSLA", "NVDA", "AAPL", "MSFT", "AMD"]
    start_date = "2022-01-01"
    end_date = "2024-01-01"

    for symbol in symbols:
        data = get_data(symbol, start_date, end_date)
        cerebro.adddata(data, name=symbol)

    cerebro.broker.setcommission(commission=0.001)

    # 4️⃣ 加入績效分析器
    cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name="annual_return")  # 年化報酬率
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.02)  # 夏普比率
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")  # 最大回撤

    # 5️⃣ 執行回測
    print("🚀 啟動回測...")
    results = cerebro.run()
    strat = results[0]  # 獲取策略結果

    # 6️⃣ 顯示績效指標
    print("✅ 回測結束，資金餘額:", cerebro.broker.getvalue())

    # 年化報酬率
    print("📊 年化報酬率:")
    for year, ret in strat.analyzers.annual_return.get_analysis().items():
        print(f"  {year}: {ret:.2%}")

    # 夏普比率
    sharpe_ratio = strat.analyzers.sharpe.get_analysis().get("sharperatio", None)
    print(f"📈 夏普比率: {sharpe_ratio:.2f}" if sharpe_ratio else "📈 夏普比率: 無法計算")

    # 最大回撤
    drawdown = strat.analyzers.drawdown.get_analysis()
    print(f"📉 最大回撤: {drawdown['max']['drawdown']:.2f}%")

    # 7️⃣ 繪製績效圖
    # cerebro.plot()

# 執行回測
run_backtest()

