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
    # Need init of market
    MARKET_OPEN_TIME = None
    MARKET_CLOSE_TIME = None
    MARKET_UPDATE_TIME = None

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
        """
        Initializes the Market manager.

        Manages different market data providers (e.g., FindMind, TWSE, Yahoo)
        and provides a unified interface to access market data.

        Args:
            market (str, optional): The name of the market provider to use initially.
                                    If None, defaults to the first provider in the list.
        """
        self.__market_list = [FindMind, TWSE, Yahoo]
        self.instance = None
        self.cached_stock_info_frame = None
        self.time = MarketTime

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
        """
        Sets the base path for caching market data for all providers.

        Args:
            data_path (str): The directory path where market data should be cached.
        """
        dbg_trace(f'set data path to {data_path}')
        for each_market in self.__market_list:
            each_market.CACHED_DATA_PATH = data_path

    def __filter_by_start_date(self, df: pd.DataFrame, start_date: str, date_column: str = 'Date') -> pd.DataFrame:
        """
        Filter the DataFrame to include only rows where the specified `date_column`
        is on or before the `start_date`. This is a helper method, typically used internally.

        Parameters:
            df (pd.DataFrame): The input DataFrame.
            start_date (str): The cutoff date in 'YYYY-MM-DD' format.
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
    def get_provider(self) -> str:
        """
        Returns the name of the currently active market data provider.

        Returns:
            str: The name of the current market data provider (e.g., 'findmind', 'twse').
        """
        return self.instance.NAME

    def get_markget_list(self) -> list[str]:
        """
        Returns a list of all available market data provider names.

        Returns:
            list[str]: A list of strings, where each string is the name of a provider.
        """
        return [ each_market.NAME for each_market in self.__market_list]

    def switch_market(self, market: str):
        """
        Switches the active market data provider.

        Args:
            market (str): The name of the market provider to switch to.
                          Must be one of the names returned by `get_markget_list()`.
        """
        for each_market in self.__market_list:
            if market == each_market.NAME:
                self.instance = each_market()

        self.time.MARKET_OPEN_TIME = self.instance.MARKET_OPEN_TIME
        self.time.MARKET_CLOSE_TIME = self.instance.MARKET_CLOSE_TIME
        self.time.MARKET_UPDATE_TIME = self.instance.MARKET_UPDATE_TIME

    def get_top_product_list(self, number = 50):
        if number > 50:
            dbg_warning('Number should not bigger then 50.')
            number = 50
        top_tw_stocks = [
            '2330', '2454', '2317', '2308', '2382', '2891', '2303', '2881', '3711', '6505',
            '2412', '2882', '2886', '2327', '3034', '2884', '6669', '2885', '5880', '3045',
            '2892', '2002', '3037', '2603', '3231', '1101', '1216', '1301', '1303', '1326',
            '1402', '2105', '2207', '2301', '2357', '2395', '2474', '2609', '2615', '2801',
            '2880', '2883', '2887', '2888', '2890', '2912', '3008', '3017', '4904', '4938',
            '5871', '8069'
        ]
        return top_tw_stocks[:number]

    def get_product_list_by_date(self, start_date: str = "2020-01-01") -> list[str]:
        """
        Retrieves a list of product IDs (stock codes) that were listed on or before a given start date.
        This method uses the currently active market data provider to fetch the product list.

        Args:
            start_date (str, optional): The date in 'YYYY-MM-DD' format. Only products
                                        listed on or before this date will be included.
                                        Defaults to "2020-01-01".

        Returns:
            list[str]: A list of product IDs (strings).
        """
        product_frame_list = self.instance.get_data_list()
        self.__filter_by_start_date(product_frame_list, start_date, "start")
        product_list = []
        for each_key, each_product_row in product_frame_list.iterrows():
            # dbg_info(f"Download code:{each_product_row['code']}, type:{each_product_row['type']}, name:{each_product_row['name']}, market:{each_product_row['market']}")
            product_list.append(each_key)
        return product_list

    def get_data_list(self, market: str = None, country: str = None) -> list[str]:
        """
        Retrieves a comprehensive list of product IDs (stock codes) available from the
        currently active market data provider.

        The results are cached internally for `get_data_info` lookup.

        Args:
            market (str, optional): Filters products by market type (e.g., 'listed', 'otc').
                                    If None, no market filtering is applied by this method,
                                    but the underlying provider might have defaults.
            country (str, optional): Filters products by country (e.g., 'TW').
                                     If None, no country filtering is applied.

        Returns:
            list[str]: A list of product IDs (strings).
        """
        # NOTE, it's more easy to get data form TWSE. all we want is listed data.
        # twse_ins = TWSE()
        # product_frame_list = twse_ins.get_data_list(market = market, country = country)
        product_frame_list = self.instance.get_data_list(market = market, country = country)

        self.cached_stock_info_frame = product_frame_list
        product_list = []
        for each_key, each_product_row in product_frame_list.iterrows():
            # dbg_info(each_key)
            # dbg_info(f"Download code:{each_product_row['code']}, type:{each_product_row['type']}, name:{each_product_row['name']}, market:{each_product_row['market']}")
            product_list.append(each_key)
        return product_list

    def get_data(self, product_id: str, start_date: datetime.date = None, end_date: datetime.date = None, force_update: bool = False) -> pd.DataFrame:
        """
        Downloads historical daily data for a given product ID from the active provider.
        The data includes Open, High, Low, Close, Volume, Turnover, Change, and Transaction.
        Prices are typically adjusted for corporate actions (e.g., dividends, splits) if the
        provider supports adjusted data or if the adjustment logic is implemented.

        Args:
            product_id (str): The unique identifier for the product (e.g., stock ticker symbol).
            start_date (datetime.date, optional): The start date for the historical data.
                                                  If None, the provider's default earliest date is used.
            end_date (datetime.date, optional): The end date for the historical data.
                                                If None, the current date is used.
            force_update (bool, optional): If True, forces a fresh download from the provider,
                                           bypassing any local cache. Defaults to False.

        Returns:
            pd.DataFrame: A DataFrame containing historical data with 'Date' as index,
                          and columns like 'Open', 'High', 'Low', 'Close', 'Volume', etc.
                          Returns an empty DataFrame if data cannot be fetched.
        """
        # FIXME, sanity check product_id.
        return self.instance.get_data(product_id=product_id, start_date=start_date, end_date=end_date,force_update = force_update)

    def get_data_info(self, product_id: str) -> dict:
        """
        Retrieves detailed information about a specific product.

        This method first attempts to use a cached list of product information.
        If the cache is empty, it will call `get_data_list()` to populate it.

        Args:
            product_id (str): The unique identifier for the product (e.g., stock ticker symbol).

        Returns:
            dict: A dictionary containing product details such as 'code', 'type', 'name',
                  'start' (listing date), 'market', 'category', and 'country'.
                  Returns None if the product information cannot be found.
        """
        # return the following info.
        # {'code': '2330', 'type': '股票', 'name': '台積電', 'start': '1994-09-05', 'market': 'listed', 'category': '半導體業', 'country': 'TW'}
        if self.cached_stock_info_frame is None:
            # Update cached buffer
            self.get_data_list()

        try:
            pd_info = self.cached_stock_info_frame
            product_dict = pd_info.loc[product_id].to_dict()
            product_dict['code'] = product_id
            return product_dict
        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return None

    def update_data(self, product_list: list[str] = [], force_update: bool = False) -> bool:
        """
        Updates historical data for a list of specified products.
        This method iterates through the `product_list` and calls the underlying
        provider's data download method for each product.

        Args:
            product_list (list[str], optional): A list of product IDs (strings) to update.
                                                If empty, the behavior depends on the underlying
                                                provider's `update_data` implementation (usually
                                                means no specific products are updated).
                                                Defaults to an empty list.
            force_update (bool, optional): If True, forces a fresh download from the provider,
                                           bypassing any local cache for each product.
                                           Defaults to False.

        Returns:
            bool: True if the update process completes (even if some individual updates fail),
                  False if a critical error prevents the process from starting.
        """
        try:
            if len(product_list) == 0:
                dbg_warning('Ignore update, empty list.')
            else:
                self.instance.update_data(product_list = product_list, force_update = force_update)
        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return False
        return True

