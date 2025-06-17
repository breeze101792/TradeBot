# system file
import traceback
import time
import threading

# FIXME, may be remove latter
import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta, date

# Local file
from utility.debug import *
from core.database import *
from core.config import *
from market.dataprovider import *
from market.product.constant import ProductType

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
    NON_TRADING_DAYS = set() # Use a set for faster lookup

    @staticmethod
    def add_non_trading_day(new_date: date):
        """
        Adds a single non-trading day (holiday, market closure) to the list.
        Existing non-trading days that are outside the valid one-week range will be removed.
        Args:
            new_date (datetime.date): A datetime.date object representing the non-trading day to add.
        """
        current_date = date.today()
        min_date = current_date - timedelta(days=7)
        max_date = current_date + timedelta(days=7)

        # Clean up existing non-trading days
        cleaned_non_trading_days = set()
        for d in MarketTime.NON_TRADING_DAYS:
            if min_date <= d <= max_date:
                cleaned_non_trading_days.add(d)
            else:
                dbg_warning(f"Existing non-trading day {d.strftime('%Y-%m-%d')} is now outside the allowed one-week range "
                            f"({min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}) and will be removed.")
        MarketTime.NON_TRADING_DAYS = cleaned_non_trading_days

        # Add the new date if it's within the valid range
        if min_date <= new_date <= max_date:
            if new_date not in MarketTime.NON_TRADING_DAYS:
                MarketTime.NON_TRADING_DAYS.add(new_date)
                dbg_info(f"Add {new_date} to NON_TRADING_DAYS")
        else:
            dbg_warning(f"New non-trading day {new_date.strftime('%Y-%m-%d')} is outside the allowed one-week range "
                        f"({min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}) and will not be added.")

    @staticmethod
    def _is_trading_day(date_obj: date) -> bool:
        """
        Checks if a given date is a trading day (Monday-Friday and not in NON_TRADING_DAYS).
        """
        return date_obj.weekday() < 5 and date_obj not in MarketTime.NON_TRADING_DAYS

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

        # Start checking from today or tomorrow
        check_date = current_time.date()
        if current_time >= target_datetime_today:
            # If target time already passed today, start checking from tomorrow
            check_date += timedelta(days=1)

        # Find the next valid trading day
        while not MarketTime._is_trading_day(check_date):
            check_date += timedelta(days=1)

        next_target_datetime = datetime.combine(check_date, target_time)

        return next_target_datetime

    @staticmethod
    def get_next_market_update_time() -> datetime:
        """
        Calculates the next expected market data update time using the helper method.
        Assumes updates happen at MARKET_UPDATE_TIME on trading days.
        """
        return MarketTime._get_next_trading_day_time(MarketTime.MARKET_UPDATE_TIME)

    @staticmethod
    def get_next_market_close_time() -> datetime:
        """
        Calculates the next market closing time using the helper method.
        Assumes the market close at MARKET_CLOSE_TIME on trading days.
        """
        return MarketTime._get_next_trading_day_time(MarketTime.MARKET_CLOSE_TIME)

    @staticmethod
    def get_next_market_open_time() -> datetime:
        """
        Calculates the next market opening time using the helper method.
        Assumes the market opens at MARKET_OPEN_TIME on trading days.
        """
        return MarketTime._get_next_trading_day_time(MarketTime.MARKET_OPEN_TIME)

    @staticmethod
    def is_trading_day() -> bool:
        """
        Checks if the current day is a trading day (Monday to Friday and not in NON_TRADING_DAYS).
        """
        current_date = datetime.now().date()
        return MarketTime._is_trading_day(current_date)

    @staticmethod
    def get_previous_market_update_time() -> datetime:
        """
        Calculates the previous expected market data update time.
        Assumes updates happen at MARKET_UPDATE_TIME on trading days.
        """
        current_time = datetime.now()
        update_time_today = current_time.replace(
            hour=MarketTime.MARKET_UPDATE_TIME.hour,
            minute=MarketTime.MARKET_UPDATE_TIME.minute,
            second=0,
            microsecond=0
        )

        # Determine the starting point for checking previous day
        check_date = current_time.date()
        if current_time < update_time_today:
            # If current time is before today's update time, check yesterday first
            check_date -= timedelta(days=1)

        # Find the previous valid trading day
        while not MarketTime._is_trading_day(check_date):
            check_date -= timedelta(days=1)

        previous_update_date_dt = datetime.combine(check_date, MarketTime.MARKET_UPDATE_TIME)

        return previous_update_date_dt

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

    def get_data_list(self, market: str = None, country: str = None, product_type: ProductType = ProductType.STOCK) -> list[str]:
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
        product_frame_list = self.instance.get_data_list(market = market, country = country, product_type = product_type)

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
        if end_date is None or end_date > MarketTime.get_previous_market_update_time().date():
            end_date = MarketTime.get_previous_market_update_time().date()
            if end_date is not None:
                dbg_debug(f"Change {end_date} to {MarketTime.get_previous_market_update_time().date()}")

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

    def update_data(self, product_list: list[str] = [], force_update: bool = False, update_trading_day = False) -> bool:
        """
        Updates historical data for a list of specified products.
        This method iterates through the `product_list` and calls the underlying
        provider's data download method for each product.

        Args:
            product_list (list[str], optional): A list of product IDs (strings) to update.
                                                If empty, the behavior depends on the underlying
                                                provider's `update_data` implementation (usually
                                                means update all).
                                                Defaults to an empty list.
            force_update (bool, optional): If True, forces a fresh download from the provider,
                                           bypassing any local cache for each product.
                                           Defaults to False.
            update_trading_day (bool, optional): If True, and the underlying provider's `update_data`
                                                 method returns a `datetime.date` object (indicating
                                                 a non-trading day), that date will be added to
                                                 `MarketTime.NON_TRADING_DAYS`. Defaults to False.

        Returns:
            bool: True if the update process completes (even if some individual updates fail),
                  False if a critical error prevents the process from starting.
        """
        try:
            result = self.instance.update_data(product_list = product_list, force_update = force_update)
            if update_trading_day is True and result is not True and isinstance(result, date):
                MarketTime.add_non_trading_day(result)
        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return False
        return True

