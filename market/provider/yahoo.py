import pandas as pd
import traceback
import os

from datetime import datetime
import yfinance as yf

from utility.debug import *
from market.dataprovider import *

class Yahoo(DataProvider):
    NAME='yahoo'
    def __init__(self):
        super().__init__()

    def download_data(self, ticker: str, period: int = 0):
        yf_code = ticker + '.TW'
        if period == 0:
            period = 'max'
        else:
            period = period.__str__()

        if period is not None:
            dbg_info(f"Download {yf_code} period:{period}")
            df = yf.Ticker(yf_code).history(period=period)
        # elif start_date is not None and end_date is not None:
        #     df = yf.download(yf_code, start=start_date, end=end_date, multi_level_index=False)
        else:
            dbg_info(f"Download {yf_code} period:max")
            df = yf.Ticker(yf_code).history(period="max")

        return df
    # def get_ticker(self, ticker: str, start_date: str = None, end_date: str = None, period: str = None, force_update: bool = False):
    #     # ticker = "8069.TWO"  # name from Yahoo Finance
    #     # start_date = "2018-01-01"
    #     # end_date = "2025-01-01"
    #     cache_data_name = './data'
    #     ticker_local_file = ticker.__str__() + ".csv"
    #
    #     # Download stock data
    #     df = Yahoo.load_from_csv(ticker_local_file, 'Date', folder=cache_data_name)
    #     if df is None and force_update:
    #         if period is not None:
    #             df = yf.Ticker(ticker).history(period=period)
    #         elif start_date is not None and end_date is not None:
    #             df = yf.download(ticker, start=start_date, end=end_date, multi_level_index=False)
    #         else:
    #             df = yf.Ticker(ticker).history(period="max")
    #         Yahoo.save_to_csv(df, ticker_local_file, folder=cache_data_name)
    #     else:
    #         dbg_debug(f"DataFrame loaded from {ticker_local_file}")
    #
    #     # Check if data download ok
    #     if df.empty:
    #         raise ValueError("Fail to download data from Yahoo Finance, Please check your sotkc id or net work connection.")
    #     # else:
    #     #     print("Data download successfully！Showing first few lines：")
    #     #     print(df.head())
    #     return df
