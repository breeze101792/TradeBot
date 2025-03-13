import pandas as pd
import traceback
import os

import time
from datetime import datetime

from utility.debug import *
from market.dataprovider import *

import twstock
from twstock import Stock


# 2. 定義 Backtrader 的 DataFeed，並保留完整數據
# class PandasData(bt.feeds.PandasData):
#     params = (
#         ('Date', 0),
#         ('Open', 1),
#         ('High', 2),
#         ('Low', 3),
#         ('Close', 4),
#         ('Volume', 5),
#         ('Turnover', 6),    # 新增成交金額
#         ('Change', 7),      # 新增漲跌
#         ('Transaction', 8), # 新增成交筆數
#         ('Openinterest', -1),  # 無 Open Interest
#     )

class TWSE(DataProvider):
    def __init__(self):
        self.ticker_local_path='./data/twse'

    # def __download_data_list(self, product_id: str, period: str = None):
    #     # print(twstock.codes)                # 列印台股全部證券編碼資料
    #     for each_id in twstock.codes.keys():
    #         each_stock = twstock.codes[each_id]
    #         try:
    #             if each_stock.type != '股票':
    #                 continue
    #             # StockCodeInfo(type='股票', code='2330', name='台積電', ISIN='TW0002330008', start='1994/09/05', market='上市', group='半導體業', CFI='ESVUFR')
    #             print(f"Type{each_stock.type}, code={each_stock.code}, name={each_stock.name}, start={each_stock.start}, market={each_stock.market}, group={each_stock.group}")
    #         except Exception as e:
    #             print(each_stock)
    #             print(e)
    #             break
    #     return 

    def download_data_list(self, market: str = None, country: str = None):
        product_list = []

        for each_id in twstock.codes.keys():
            each_stock = twstock.codes[each_id]
            try:
                if each_stock.type != '股票':
                    continue
                
                # 整理資料
                product_data = {
                    "code": each_stock.code,
                    "type": each_stock.type,
                    "name": each_stock.name,
                    "start": pd.to_datetime(each_stock.start, errors='coerce').strftime('%Y-%m-%d') if each_stock.start else None,
                    "market": self.convert_market(each_stock.market),
                    "category": each_stock.group,
                    "country": "TW",
                }
                product_list.append(product_data)

            except Exception as e:
                print(f"Error processing stock: {each_stock}")
                print(e)
                continue

        # 轉換成 Pandas DataFrame
        df = pd.DataFrame(product_list)

        # 插入資料庫
        # for _, row in df.iterrows():
        #     self.add_product(
        #         product_id=row["code"],
        #         product_type=row["type"],
        #         name=row["name"],
        #         start=row["start"],
        #         market=row["market"],
        #         country=row["country"],
        #         group=row["group"],
        #         tracking=row["tracking"]
        #     )

        return df

    def convert_market(self, market_str):
        """ 轉換市場名稱 """
        market_map = {
            "上市": "listed",
            "上櫃": "otc",
            "興櫃": "emerging"
        }
        return market_map.get(market_str, "unknown")

    # 1. Get history data
    def download_data(self, ticker: str, period: int = 5):
        #
        # ticker_local_path = './data_twse'
        # ticker_local_file = stock_id + ".csv"
        # df = load_from_csv(ticker_local_file, 'Date', folder=ticker_local_path)
        # if df is not None:
        #     return df

        # print(twstock.codes[ticker].name)   # 列印 2330 證券名稱
        # print(twstock.codes[ticker].start)  # 列印 2330 證券上市日期
        #
        # stock = Stock(ticker)
        # print(stock)
        # print(stock.fetch_from(2024, 3))

        # dbg_debug(f"get {ticker} from TWSE")
        stock = Stock(ticker)
        # dbg_debug(f"Done getting {ticker}")
        data_list = []

        # 取得歷史資料
        for d in stock.fetch_from(datetime.now().year - period, 1):
            # 確保日期是 datetime 格式
            date = pd.to_datetime(str(d.date))  # 轉換成 datetime

            # 驗證數據是否完整
            if None in [date, d.open, d.high, d.low, d.close, d.capacity, d.turnover, d.transaction]:
                print(f"⚠️ Ignore invalid data: {d}")
                continue

            # 驗證價格數據
            if d.open <= 0 or d.high <= 0 or d.low <= 0 or d.close <= 0:
                print(f"⚠️ Skip invalid price: {d}")
                continue

            # 驗證成交量數據
            if d.capacity < 0 or d.turnover < 0 or d.transaction < 0:
                print(f"⚠️ Invalid trading data: {d}")
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
        # print(df.head())
        # prevent been ban
        dbg_debug("Sleeping for 1 seconds.")
        time.sleep(1)
        # save_to_csv(df, ticker_local_file, folder=ticker_local_path)
        return df
