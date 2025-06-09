import pandas as pd
import traceback
import os

import time
from datetime import datetime

from utility.debug import *
from market.dataprovider import *

import twstock
from twstock import Stock
from broker.order.constant import OrderPrice

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
    NAME='twse'

    MARKET_OPEN_TIME = dt_time(9, 0, 0)
    MARKET_CLOSE_TIME = dt_time(13, 30, 0)
    MARKET_UPDATE_TIME = dt_time(18, 00, 0) # Time when daily data is usually finalized
    def __init__(self):
        super().__init__()

    def get_current_price(self, symbol, price_type:OrderPrice = OrderPrice.BID) -> float:
        # price_type => bid/ask/trade
        result = None
        # this is for mock broker, don't use it on real code.
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # dbg_info(f'get_current_price : {symbol}')
                result = twstock.realtime.get(symbol)
                # dbg_info('Realtime info:', result)
                trade = result.get('realtime').get('latest_trade_price')
                bid = result.get('realtime').get('best_bid_price')[0]
                ask = result.get('realtime').get('best_ask_price')[0]
                if price_type == OrderPrice.BID:
                    return float(bid)
                elif price_type == OrderPrice.ASK:
                    return float(ask)
                elif price_type == OrderPrice.LAST:
                    return float(trade)
                else:
                    return 0
            except ValueError:
                dbg_debug(f'[{symbol}] value error: {result}. Attempt {attempt + 1}/{max_retries}')
                time.sleep(1) # Wait a bit before retrying
            except Exception as e:
                dbg_error(f'Error found on {symbol}. Attempt {attempt + 1}/{max_retries}')
                dbg_error(e)
                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                time.sleep(1) # Wait a bit before retrying
        dbg_error(f'Failed to get current price for {symbol} after {max_retries} attempts.')
        return 0.0

    def download_data_list(self, market: str = None, country: str = None):
        product_list = []

        for each_id in twstock.codes.keys():
            each_stock = twstock.codes[each_id]
            try:
                if each_stock.type != '股票':
                    continue
                if each_stock.market != '上市':
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
                dbg_error(f"Error processing stock: {each_stock}")
                dbg_error(e)
                continue

        # 轉換成 Pandas DataFrame
        df = pd.DataFrame(product_list)

        if not df.empty:
            df.set_index('code', inplace=True)

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
    def download_data(self, product_id: str, start_date: datetime.date = None, end_date: datetime.date = None):
        fetch_start_year = 2000
        fetch_start_month = 1

        if start_date:
            fetch_start_year = start_date.year
            fetch_start_month = start_date.month
        else:
            # If start_date is not provided, try to get the earliest available date for the stock
            stock_info = twstock.codes.get(product_id)
            if stock_info and stock_info.start:
                try:
                    stock_start_dt = datetime.strptime(stock_info.start, "%Y/%m/%d")
                    fetch_start_year = stock_start_dt.year
                    fetch_start_month = stock_start_dt.month
                except ValueError:
                    dbg_warning(f"Could not parse start date for {product_id}: {stock_info.start}. Defaulting to 2000/1.")
                    fetch_start_year = 2000
                    fetch_start_month = 1
            else:
                dbg_warning(f"No start date found for {product_id}. Defaulting to 2000/1.")
                fetch_start_year = 2000
                fetch_start_month = 1

        # Ensure we don't try to fetch before 2000, as twstock data typically doesn't go back further
        if fetch_start_year < 2000:
            fetch_start_year = 2000
            fetch_start_month = 1

        dbg_trace(f"Download {product_id} start from {fetch_start_year}/{fetch_start_month} to {end_date if end_date else 'current date'}")

        stock = Stock(product_id)
        data_list = []

        # 取得歷史資料
        for d in stock.fetch_from(fetch_start_year, fetch_start_month):
            # 確保日期是 datetime 格式
            date = pd.to_datetime(str(d.date))  # 轉換成 datetime

            # 驗證數據是否完整
            if None in [date, d.open, d.high, d.low, d.close, d.capacity, d.turnover, d.transaction]:
                dbg_warning(f"⚠️ Ignore invalid data: {d}")
                continue

            # 驗證價格數據
            if d.open <= 0 or d.high <= 0 or d.low <= 0 or d.close <= 0:
                dbg_warning(f"⚠️ Skip invalid price: {d}")
                continue

            # 驗證成交量數據
            if d.capacity < 0 or d.turnover < 0 or d.transaction < 0:
                dbg_warning(f"⚠️ Invalid trading data: {d}")
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

        # Filter by end_date if provided
        if end_date:
            df = df[df.index.date <= end_date]

        # prevent been ban
        time.sleep(1)
        return df
