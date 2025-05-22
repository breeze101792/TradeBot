# system file
import traceback
import time
import threading

# FIXME, may be remove latter
import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta

# Local file
from utility.debug import *
from core.database import *
from core.config import *
from market.dataprovider import *

from market.provider.yahoo import *
from market.provider.twse import *
from market.provider.findmind import *
from datetime import time as dt_time # Alias to avoid conflict with time module

class MarketTime:
    # Standard market times (e.g., for TWSE)
    # TODO: Make these market-specific if needed
    MARKET_OPEN_TIME = dt_time(9, 0, 0)
    MARKET_CLOSE_TIME = dt_time(13, 30, 0)
    MARKET_UPDATE_TIME = dt_time(13, 40, 0) # Time when daily data is usually finalized

    @staticmethod
    def get_market_open_time() -> dt_time:
        """Returns the standard market opening time."""
        return MarketTime.MARKET_OPEN_TIME

    @staticmethod
    def get_market_close_time() -> dt_time:
        """Returns the standard market closing time."""
        return MarketTime.MARKET_CLOSE_TIME

    @staticmethod
    def _get_next_trading_day_time(target_time: dt_time) -> datetime:
        """
        Helper method to find the next datetime for a specific time on a trading day.
        """
        current_time = datetime.now()
        target_datetime_today = current_time.replace(
            hour=target_time.hour,
            minute=target_time.minute,
            second=0,
            microsecond=0
        )

        if current_time.weekday() < 5:  # Monday-Friday
            # If current time is before the target time today
            if current_time < target_datetime_today:
                next_target_datetime = target_datetime_today
            else:
                # Target time already passed today, find next trading day
                next_day = current_time + timedelta(days=1)
                while next_day.weekday() >= 5: # Skip weekends
                    next_day += timedelta(days=1)
                next_target_datetime = next_day.replace(
                    hour=target_time.hour,
                    minute=target_time.minute,
                    second=0,
                    microsecond=0
                )
        else: # Saturday or Sunday
            # Find next trading day (Monday)
            days_until_monday = 7 - current_time.weekday()
            next_day = current_time + timedelta(days=days_until_monday)
            next_target_datetime = next_day.replace(
                hour=target_time.hour,
                minute=target_time.minute,
                second=0,
                microsecond=0
            )

        return next_target_datetime

    @staticmethod
    def get_next_market_update_time() -> datetime:
        """
        Calculates the next expected market data update time using the helper method.
        Assumes updates happen at MARKET_UPDATE_TIME on trading days (Mon-Fri).
        """
        return MarketTime._get_next_trading_day_time(MarketTime.MARKET_UPDATE_TIME)

    @staticmethod
    def get_next_market_close_time() -> datetime:
        """
        Calculates the next market opening time using the helper method.
        Assumes the market close at MARKET_CLOSE_TIME on trading days (Mon-Fri).
        """
        return MarketTime._get_next_trading_day_time(MarketTime.MARKET_CLOSE_TIME)

    @staticmethod
    def get_next_market_open_time() -> datetime:
        """
        Calculates the next market opening time using the helper method.
        Assumes the market opens at MARKET_OPEN_TIME on trading days (Mon-Fri).
        """
        return MarketTime._get_next_trading_day_time(MarketTime.MARKET_OPEN_TIME)

    @staticmethod
    def is_trading_day() -> bool:
        """
        Checks if the current day is a trading day (Monday to Friday).
        """
        current_time = datetime.now()
        return current_time.weekday() < 5  # 0=Monday, 1=Tuesday, ..., 4=Friday

    @staticmethod
    def get_previous_market_update_time() -> datetime:
        """
        Calculates the previous expected market data update time.
        Assumes updates happen at MARKET_UPDATE_TIME on trading days (Mon-Fri).
        """
        current_time = datetime.now()
        update_time_today = current_time.replace(
            hour=MarketTime.MARKET_UPDATE_TIME.hour,
            minute=MarketTime.MARKET_UPDATE_TIME.minute,
            second=0,
            microsecond=0
        )

        if current_time.weekday() < 5:  # Monday-Friday
            # If current time is after today's update time, the previous update was today.
            if current_time >= update_time_today:
                previous_update_date = update_time_today
            else:
                # Otherwise, the previous update was on the last trading day.
                previous_day = current_time - timedelta(days=1)
                # Skip backwards over weekend days
                while previous_day.weekday() >= 5:
                    previous_day -= timedelta(days=1)
                previous_update_date = previous_day.replace(
                    hour=MarketTime.MARKET_UPDATE_TIME.hour,
                    minute=MarketTime.MARKET_UPDATE_TIME.minute,
                    second=0,
                    microsecond=0
                )
        else:  # Saturday or Sunday
            # The previous update was on the last trading day (Friday).
            previous_day = current_time - timedelta(days=(current_time.weekday() - 4)) # Days since last Friday
            previous_update_date = previous_day.replace(
                hour=MarketTime.MARKET_UPDATE_TIME.hour,
                minute=MarketTime.MARKET_UPDATE_TIME.minute,
                second=0,
                microsecond=0
            )

        return previous_update_date

class Market:
    def __init__(self, market = None):
        # TODO, after solving cache issue, swtich to FindMind by default.
        self.__market_list = [TWSE, FindMind, Yahoo]
        self.instance = None
        self.cached_stock_info_frame = None

        # config
        self.cm = AppConfigManager()
        self.set_cached_path(self.cm.get_path('data'))

        # post init
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

    def set_cached_path(self, data_path):
        dbg_trace(f'set data path to {data_path}')
        for each_market in self.__market_list:
            each_market.CACHED_DATA_PATH = data_path

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

    def get_top_product_list(self, number = 50):
        if number > 50:
            dbg_warning('Number should not bigger then 50.')
            number = 50
        # top_tw_stocks = [
        #     "2330", "2454", "2317", "2881", "2308",
        #     "2882", "2412", "2382", "2891", "3711",
        #     "2886", "2303", "1301", "1303", "1216",
        #     "2884", "6669", "2885", "5880", "3045"
        # ]
        top_tw_stocks = [
            '2330', '2454', '2317', '2308', '2382', '2891', '2303', '2881', '3711', '6505',
            '2412', '2882', '2886', '2327', '3034', '2884', '6669', '2885', '5880', '3045',
            '2892', '2002', '3037', '2603', '3231', '1101', '1216', '1301', '1303', '1326',
            '1402', '2105', '2207', '2301', '2357', '2395', '2474', '2609', '2615', '2801',
            '2880', '2883', '2887', '2888', '2890', '2912', '3008', '3017', '4904', '4938',
            '5871', '8069'
        ]
        return top_tw_stocks[:number]

    def get_product_list_by_date(self, start_date = "2020-01-01"):
        product_frame_list = self.instance.get_data_list()
        self.__filter_by_start_date(product_frame_list, start_date, "start")
        product_list = []
        for _, each_product_row in product_frame_list.iterrows():
            # dbg_info(f"Download code:{each_product_row['code']}, type:{each_product_row['type']}, name:{each_product_row['name']}, market:{each_product_row['market']}")
            product_list.append(each_product_row['code'])
        return product_list
    # def get_data_list_filtered(self, market: str = None, country: str = None):
    #     # return self.instance(market = market, conuntry = country)
    #     product_frame_list = self.instance(market = market, conuntry = country)
    #     product_list = []
    #     for _, each_product_row in product_frame_list.iterrows():
    #         # dbg_info(f"Download code:{each_product_row['code']}, type:{each_product_row['type']}, name:{each_product_row['name']}, market:{each_product_row['market']}")
    #         product_list.append(each_product_row['code'])
    #     return product_list

    def get_data_list(self, market: str = None, country: str = None):
        product_frame_list = self.instance.get_data_list(market = market, country = country)
        self.cached_stock_info_frame = product_frame_list
        product_list = []
        for _, each_product_row in product_frame_list.iterrows():
            # dbg_info(f"Download code:{each_product_row['code']}, type:{each_product_row['type']}, name:{each_product_row['name']}, market:{each_product_row['market']}")
            product_list.append(each_product_row['code'])
        return product_list

    def get_data(self, product_id: str, period: str = None, force_update: bool = False):
        # FIXME, sanity check product_id.
        return self.instance.get_data(product_id=product_id, period=period, force_update = force_update)

    def get_data_info(self, product_id):
        # return the following info.
        # {'code': '2330', 'type': '股票', 'name': '台積電', 'start': '1994-09-05', 'market': 'listed', 'category': '半導體業', 'country': 'TW'}
        if self.cached_stock_info_frame is None:
            # Update cached buffer
            self.get_data_list()

        try:
            pd_info = self.cached_stock_info_frame
            return pd_info[pd_info['code'] == product_id].iloc[0].to_dict()
        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return None

    def update_data(self, force_update: bool = False):
        product_frame_list = self.instance.get_data_list()
        product_amount = len(product_frame_list)
        dbg_info(f"Start update data.")
        for idx, each_product_row in product_frame_list.iterrows():
            # Use space to avoid error message been erase.
            dbg_info(f"[{idx}/{product_amount}] Download code:{each_product_row['code']}, type:{each_product_row['type']}, name:{each_product_row['name']}, market:{each_product_row['market']}", prefix='\r', end=' ' * 10)
            try:
                self.instance.get_data(product_id = each_product_row['code'], force_update = force_update)
            except Exception as e:
                dbg_error(f"Error updateing stock: {each_product_row['code']}")
                dbg_error(e)
                time.sleep(1)
                continue
        dbg_info(f"All {product_amount} has been update to date.", prefix='\n')

    # This method seems redundant now that the logic is in MarketTime.get_next_market_update_time
    # Consider removing it or calling the MarketTime method from here if needed.
    # def get_next_market_date(self):
    #     return MarketTime.get_next_market_update_time()

