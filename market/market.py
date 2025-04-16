# system file
import traceback
import time
import threading

# FIXME, may be remove latter
import backtrader as bt
import pandas as pd
from datetime import datetime

# Local file
from utility.debug import *
from core.database import *
from market.dataprovider import *

from market.provider.yahoo import *
from market.provider.twse import *

class Market:
    def __init__(self, market = None):
        self.__market_list = [ TWSE, Yahoo ]
        self.instance = None

        if market is not None:
            self.switch_market(market)
        else:
            self.switch_market(self.__market_list[0].NAME)

        dbg_debug(f'Init market to {self.instance.NAME}')
    # def __set_market(self, instance):
    #     self.NAME = instance.NAME
    #     self.instance = instance
    #     self.cache_data_name = self.instance.cache_data_name
    #     self.download_data_list = self.instance.download_data_list
    #     self.download_data = self.instance.download_data

    def __filter_by_start_date(self, df: pd.DataFrame, start_date: str, date_column: str = 'Date') -> pd.DataFrame:
        """
        Filter the DataFrame to include only rows with date_column >= start_date.

        Parameters:
            df (pd.DataFrame): The input DataFrame.
            start_date (str): The start date in 'YYYY-MM-DD' format.
            date_column (str): The column name that contains date values. Default is 'Date'.

        Returns:
            pd.DataFrame: Filtered DataFrame.
        """
        # Convert the date column to datetime
        df[date_column] = pd.to_datetime(df[date_column])
        start_date = pd.to_datetime(start_date)

        # Apply filtering
        filtered_df = df[df[date_column] <= start_date].reset_index(drop=True)
        return filtered_df
    ## API From other files.
    def get_provider(self):
        return self.instance.NAME
    def get_markget_list(self):
        return [ each_market.NAME for each_market in self.__market_list]
    def switch_market(self, market):
        for each_market in self.__market_list:
            if market == each_market.NAME:
                self.instance = each_market()

    def get_product_list_by_date(self, start_date = "2020-01-01"):
        product_frame_list = self.instance.get_data_list()
        self.__filter_by_start_date(product_frame_list, start_date, "start")
        product_list = []
        for _, each_product_row in product_frame_list.iterrows():
            # dbg_info(f"Download code:{each_product_row['code']}, type:{each_product_row['type']}, name:{each_product_row['name']}, market:{each_product_row['market']}")
            product_list.append(each_product_row['code'])

        return product_list
    def get_top_product_list(self, number = 20):
        top_tw_stocks = [
            "2330", "2454", "2317", "2881", "2308",
            "2882", "2412", "2382", "2891", "3711",
            "2886", "2303", "1301", "1303", "1216",
            "2884", "6669", "2885", "5880", "3045"
        ]
        return top_tw_stocks

    def update_data(self):
        product_frame_list = self.instance.get_data_list()
        product_amount = len(product_frame_list)
        for idx, each_product_row in product_frame_list.iterrows():
            dbg_info(f"[{idx}/{product_amount}] Download code:{each_product_row['code']}, type:{each_product_row['type']}, name:{each_product_row['name']}, market:{each_product_row['market']}")
            try:
                self.instance.get_data(product_id = each_product_row['code'])
            except Exception as e:
                dbg_error(f"Error updateing stock: {each_product_row['code']}")
                dbg_error(e)
                time.sleep(1)
                continue

    def get_data_list_filtered(self, market: str = None, country: str = None):
        return self.instance(market = market, conuntry = conuntry)

    def get_data_list(self, market: str = None, country: str = None):
        return self.instance.get_data_list(market = market, conuntry = conuntry)

    def get_data(self, product_id: str, period: str = None):
        return self.instance.get_data(product_id=product_id, period=period)


