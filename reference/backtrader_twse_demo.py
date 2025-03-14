import twstock
import pandas as pd
import backtrader as bt
import datetime
import traceback

import pandas as pd
import os

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

# 1. 取得股票歷史數據，並驗證數據
def get_stock_data(stock_id, years=1):
    ticker_local_path = './.data/twse'
    ticker_local_file = stock_id + ".csv"
    df = load_from_csv(ticker_local_file, 'Date', folder=ticker_local_path)
    if df is not None:
        return df

    stock = twstock.Stock(stock_id)
    data_list = []

    # 取得歷史資料
    for d in stock.fetch_from(datetime.datetime.now().year - years, 1):
        # 確保日期是 datetime 格式
        date = pd.to_datetime(str(d.date))  # 轉換成 datetime

        # 驗證數據是否完整
        if None in [date, d.open, d.high, d.low, d.close, d.capacity, d.turnover, d.transaction]:
            print(f"⚠️ 跳過異常數據: {d}")
            continue

        # 驗證價格數據
        if d.open <= 0 or d.high <= 0 or d.low <= 0 or d.close <= 0:
            print(f"⚠️ 無效價格，跳過: {d}")
            continue

        # 驗證成交量數據
        if d.capacity < 0 or d.turnover < 0 or d.transaction < 0:
            print(f"⚠️ 無效成交數據，跳過: {d}")
            continue

        # 加入清理後的數據
        data_list.append([
            date,        # 日期 (修正日期格式)
            d.open,      # 開盤價
            d.high,      # 最高價
            d.low,       # 最低價
            d.close,     # 收盤價
            d.capacity,  # 成交股數 (對應 Yahoo volume)
            d.turnover,  # 成交金額
            d.change,    # 漲跌
            d.transaction, # 成交筆數
        ])
    
    # 轉換成 DataFrame
    df = pd.DataFrame(data_list, columns=["Date", "Open", "High", "Low", "Close", "Volume", "Turnover", "Change", "Transaction"])

    # **修正日期格式，確保是 Datetime**
    df["Date"] = pd.to_datetime(df["Date"])

    # 設置索引
    df.set_index("Date", inplace=True)

    # 確保數據格式正確
    df = df.astype({
        "Open": float,
        "High": float,
        "Low": float,
        "Close": float,
        "Volume": int,
        "Turnover": int,
        "Change": float,
        "Transaction": int,
    })

    print(df.head())
    save_to_csv(df, ticker_local_file, folder=ticker_local_path)
    return df

# 2. 定義 Backtrader 的 DataFeed，並保留完整數據
class PandasData(bt.feeds.PandasData):
    params = (
        ('Date', 0),
        ('Open', 1),
        ('High', 2),
        ('Low', 3),
        ('Close', 4),
        ('Volume', 5),
        ('Turnover', 6),    # 新增成交金額
        ('Change', 7),      # 新增漲跌
        ('Transaction', 8), # 新增成交筆數
        ('Openinterest', -1),  # 無 Open Interest
    )

# 3. 建立簡單策略
class TestStrategy(bt.Strategy):
    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(period=10)

    def next(self):
        if self.data.close[0] > self.sma[0]:
            self.buy()
        elif self.data.close[0] < self.sma[0]:
            self.sell()
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

# 4. 回測系統
# def run_backtest(stock_id):
#     init_crash = 1000000
#     cerebro = bt.Cerebro()
#
#     # 取得股票資料
#     df = get_stock_data(stock_id, 5)
#     print(df.head())
#
#     # 轉換成 Backtrader DataFeed
#     data = PandasData(dataname=df)
#     cerebro.adddata(data)
#
#     # 加入策略
#     # cerebro.addstrategy(TestStrategy)
#     cerebro.addstrategy(MovingAverageCrossover)
#
#     # 設定起始資金
#     cerebro.broker.set_cash(init_crash)
#     
#     # 執行回測
#     cerebro.run()
#
#     profit = (cerebro.broker.getvalue() - init_crash)/init_crash * 100
#     print(f"Profit {stock_id}: {(cerebro.broker.getvalue() - init_crash)}/{profit:.2f}%")
#     
#     # 繪圖
#     # cerebro.plot()
#
# # 5. 執行回測
# run_backtest('2330')  # 以台積電（2330）為例

def main():
    init_crash = 1000000
    total_earn = 0
    # ticker = "0050.TW"  # Yahoo Finance 上的台股代碼
    ticker_list = ["0050", "2454", "6533", "2412", "2379"]
    # strategy_list = [TestStrategy, TurtleTrading, RSIWithMA]
    strategy_list = [MovingAverageCrossover]

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
                # df = get_ticker_from_yfinance(ticker)
                # 初始化 Backtrader
                cerebro = bt.Cerebro()

                # 取得股票資料
                # df = get_stock_data(ticker, 5)
                df = get_stock_data(ticker, 10)
                # print(df.head())

                # 轉換成 Backtrader DataFeed
                # data = PandasData(dataname=df)
                data = bt.feeds.PandasData(dataname=df)
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

