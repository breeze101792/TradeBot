import pandas as pd
import traceback
import os
from time import sleep
from datetime import time as dt_time # Alias to avoid conflict with time module
from datetime import datetime, timedelta

from utility.debug import *

class DataProvider:
    NAME = 'provider'
    CACHED_DATA_PATH = './.data'
    SUPPORTED_ADJUSTED_DATA = False

    # ex. datetime.time(18, 00, 0)
    MARKET_OPEN_TIME = None
    MARKET_CLOSE_TIME = None
    MARKET_UPDATE_TIME = None

    def __init__(self):
        self.cache_data_name = f'./{self.NAME}'
        self.cache_data_root_path = self.CACHED_DATA_PATH

    @staticmethod
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
        dbg_trace(f"DataFrame saved to {file_path}")

    @staticmethod
    def load_from_csv(filename: str, date_column: str = None, folder: str = './', dtype: dict = None) -> pd.DataFrame:
        """
        Load a Pandas DataFrame from a CSV file if it exists.

        :param folder: The folder where the file is located.
        :param filename: The name of the CSV file.
        :param date_column: Name of the column containing dates (if any).
        :param dtype: Dictionary of column names and their data types.
        :return: The loaded DataFrame, or None if the file does not exist.
        """
        file_path = os.path.join(folder, filename)

        if not os.path.exists(file_path):
            # print(f"Error: {file_path} does not exist.")
            return None

        df = pd.read_csv(file_path, dtype=dtype)

        # If a date column is specified, convert it to datetime
        if date_column and date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column])
            df.set_index(date_column, inplace=True)
            # Ensure index is sorted
            df.sort_index(inplace=True)


        # print(f"DataFrame loaded from {file_path}")
        return df

    # Impl API.
    ###########################################################################
    def get_quota(self):
        # it's a fake api, if provider have quota limit, rewrite this api.
        return 999
    def download_data(self, product_id: str, start_date: datetime.date = None, end_date: datetime.date = None, period: str = None):
        dbg_error("Function not impl.")
        raise

    def download_data_list(self, market: str = None, country: str = None):
        dbg_error("Function not impl.")
        raise
    ###########################################################################
    def get_last_trading_update_date(self):
        # for real time api should not reference this api.
        now = datetime.now()
        last_trading_day = now.date()

        # If current time is before MARKET_UPDATE_TIME, data for today might not be fully updated.
        # So, consider the last trading day as yesterday.
        if self.MARKET_UPDATE_TIME and now.time() < self.MARKET_UPDATE_TIME:
            dbg_debug(f"Current time is before {self.MARKET_UPDATE_TIME}, considering previous trading day for data update.")
            last_trading_day -= timedelta(days=1)

        while last_trading_day.weekday() >= 5: # Skip weekends (Saturday=5, Sunday=6)
            last_trading_day -= timedelta(days=1)
        return last_trading_day

    def get_data_list(self, market: str = None, country: str = None, force_update: bool = False):
        data_list_cache_folder = os.path.join(self.cache_data_root_path, self.cache_data_name, 'lists')
        filename_prefix = "data_list"
        today_str = self.get_last_trading_update_date().strftime('%Y%m%d')
        current_day_filename = f"{filename_prefix}_{today_str}.csv"
        file_path = os.path.join(data_list_cache_folder, current_day_filename)

        df = None
        needs_update = force_update

        # Check if today's cached file exists
        if os.path.exists(file_path):
            df = self.load_from_csv(current_day_filename, folder=data_list_cache_folder, dtype={'code': str})
            if df is not None and not df.empty:
                # Set 'code' as index if it's a column
                if 'code' in df.columns:
                    df.set_index('code', inplace=True)
                dbg_debug(f"Loaded data list from cache: {file_path}")
            else:
                # File exists but is empty or failed to load
                dbg_debug(f"Cached data list {file_path} is empty or corrupted, forcing update.")
                needs_update = True
        else:
            dbg_debug(f"No cached data list for today found at {file_path}, forcing update.")
            needs_update = True

        if needs_update:
            dbg_trace(f"Downloading new data list for market={market}, country={country}")
            self.wait_quota(5)
            new_df = self.download_data_list(market=market, country=country)
            if new_df is not None and not new_df.empty:
                # Set 'code' as index if it's a column
                if 'code' in new_df.columns:
                    new_df.set_index('code', inplace=True)
                self.save_to_csv(new_df, current_day_filename, folder=data_list_cache_folder)
                df = new_df
            else:
                dbg_error(f"Failed to download data list for market={market}, country={country}.")
                # If download fails, try to load any existing older file as a fallback
                # For simplicity, if download fails and no valid cache, return empty.
                if df is None: # If df is still None (no valid cache was loaded initially)
                    return pd.DataFrame() # Return empty DataFrame

        if df is None or df.empty:
             dbg_error(f"No data list available for market={market}, country={country} after attempting load/download.")
             return pd.DataFrame()

        return df

    def get_data(self, product_id: str, start_date: datetime.date = None, end_date: datetime.date = None, incremental_update = False, force_update: bool = False):
        # Get today's date and last trading day
        today = datetime.now().date()
        last_trading_day = self.get_last_trading_update_date()

        data_cache_folder = ""
        if self.SUPPORTED_ADJUSTED_DATA is True:
            today_str = last_trading_day.strftime('%Y%m%d')
            data_cache_folder = os.path.join(self.cache_data_root_path, self.cache_data_name, 'datas', today_str)
        else:
            data_cache_folder = os.path.join(self.cache_data_root_path, self.cache_data_name, 'datas')

        ticker_local_path = f"{data_cache_folder}"
        ticker_local_file = product_id.__str__() + ".csv"

        # Convert start_date and end_date to datetime.date objects if they are not None
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()

        # Load existing data from cache
        df = self.load_from_csv(ticker_local_file, 'Date', folder=ticker_local_path)

        # Determine if a download is required
        # do not set it false after this line, otherwisse will break the force_update
        download_required = force_update

        # Determine download range
        download_start_date = None
        download_end_date = None

        if df is None or df.empty:
            dbg_debug(f"No cached data for {product_id} or cache is empty. Full download required.")
            download_required = True
            download_start_date = start_date if start_date else datetime(1900, 1, 1).date() # Default to very old date
            download_end_date = end_date if end_date else today
        elif incremental_update is False:
            cached_min_date = df.index.min().date()
            cached_max_date = df.index.max().date()

            # only print message of it to warn user perform update.
            if end_date and cached_max_date < end_date:
                dbg_warning(f"Cached data for {product_id} ends before requested end_date. Download required up to {end_date}.")
            elif end_date is None and cached_max_date < last_trading_day:
                dbg_warning(f"Cached data for {product_id} is not up to last trading day. Download required.")

        elif incremental_update is True:
            # to avoid double check on market close date, we disale this feature.
            # when data file is not exist, we will donwload all data. so it would be ok for us to disable it.
            # and this woruld be more robust for upper layer.
            cached_min_date = df.index.min().date()
            cached_max_date = df.index.max().date()

            # Check if cached data covers the requested range
            # We don't check the start date, cause it may not be avaliable even on server.
            # if start_date and cached_min_date > start_date:
            #     dbg_debug(f"Cached data for {product_id} starts after requested start_date. Download required from {start_date}.")
            #     download_required = True
            #     download_start_date = start_date
            #     download_end_date = cached_min_date - timedelta(days=1) # Download up to the day before cached data starts
            
            if end_date and cached_max_date < end_date:
                dbg_debug(f"Cached data for {product_id} ends before requested end_date. Download required up to {end_date}.")
                download_required = True
                if download_start_date is None: # If not already set by start_date check
                    download_start_date = cached_max_date + timedelta(days=1)
                download_end_date = end_date
            elif end_date is None and cached_max_date < last_trading_day:
                dbg_debug(f"Cached data for {product_id} is not up to last trading day. Download required.")
                download_required = True
                if download_start_date is None: # If not already set by start_date check
                    download_start_date = cached_max_date + timedelta(days=1)
                download_end_date = last_trading_day # Update to last trading day

            # If download_start_date is still None, it means we only need to update from the end of cached data
            if download_required and download_start_date is None:
                download_start_date = cached_max_date + timedelta(days=1)
                download_end_date = end_date if end_date else last_trading_day

            # Force update notify.
            if download_required and download_start_date and download_end_date and download_start_date > download_end_date:
                dbg_debug(f"Calculated download_start_date {download_start_date} is after download_end_date {download_end_date}. do force update.")

        if download_required:
            dbg_trace(f'Downloading data for {product_id} from {download_start_date} to {download_end_date}')
            self.wait_quota(5)
            new_df = self.download_data(product_id, start_date=download_start_date, end_date=download_end_date)

            if new_df is not None and not new_df.empty:
                if df is not None and not df.empty:
                    # Combine old and new data, remove duplicates, and sort by index
                    df = pd.concat([df, new_df]).drop_duplicates(keep='last').sort_index()
                else:
                    df = new_df
                self.save_to_csv(df, ticker_local_file, folder=ticker_local_path)
            else:
                dbg_debug(f"No new data downloaded for {product_id} in range {download_start_date} to {download_end_date}.")

        # Ensure df is not None before checking if it's empty
        if df is None or df.empty:
             dbg_error(f"No data available for {product_id} after attempting load/download.")
             return pd.DataFrame() # Return empty DataFrame

        # Filter the DataFrame by the requested start_date and end_date
        if start_date:
            df = df[df.index.date >= start_date]
        if end_date:
            df = df[df.index.date <= end_date]

        if df.empty:
            dbg_debug(f"No data for {product_id} in the requested range {start_date} to {end_date}.")
            return pd.DataFrame()

        dbg_debug(f"DataFrame for {product_id} loaded and filtered from {df.index.min().date()} to {df.index.max().date()}")
        return df
    def wait_quota(self, require_quota = 1):
        flag_wait = False
        # check quota if 
        while self.get_quota() < require_quota:
            try:
                # record we wait.
                flag_wait = True
                # sleep 10m
                dbg_info(f"[{datetime.now()}] Wiat for another 10 Minutes got get require quota(require_quota/{self.get_quota()}).", prefix='\r', end=' ' * 10)
                sleep(10*60)
            except Exception as e:
                raise e
        if flag_wait is True:
            dbg_info(f"Get new quota {self.get_quota()}", prefix='\n')
        else:
            dbg_info(f"Remain Quota: {self.get_quota()}", prefix='\n')

    def update_data(self, product_list = [], force_update: bool = False):
        if len(product_list) == 0:
            # Assuming get_data_list returns a DataFrame with 'code' as index
            data_list_df = self.get_data_list()
            if not data_list_df.empty:
                product_list = data_list_df.index.tolist()
            else:
                product_list = []

        product_amount = len(product_list)
        success_count = 0

        if product_amount == 0:
            dbg_info("No products to update.")
            return True # No products to update, so not a failure

        ####
        # Get today's date and last trading day
        last_trading_day = self.get_last_trading_update_date()

        data_cache_folder = ""
        if self.SUPPORTED_ADJUSTED_DATA is True:
            today_str = last_trading_day.strftime('%Y%m%d')
            data_cache_folder = os.path.join(self.cache_data_root_path, self.cache_data_name, 'datas', today_str)
        else:
            data_cache_folder = os.path.join(self.cache_data_root_path, self.cache_data_name, 'datas')

        data_update_lock_path = f"{data_cache_folder}"
        data_update_lock_file = f"update.lck"
        lock_file_full_path = os.path.join(data_update_lock_path, data_update_lock_file)

        # Check if lock file exists
        if os.path.exists(lock_file_full_path):
            dbg_info(f"Lock file {lock_file_full_path} exists. Another instance is likely updating. Skipping this update call.")
            return True # Indicate that the update was handled (by another instance)

        # Create the lock file
        os.makedirs(data_update_lock_path, exist_ok=True)
        try:
            with open(lock_file_full_path, 'w') as f:
                f.write(f"Locked by {os.getpid()} at {datetime.now()}\n")
            dbg_debug(f"Lock file created at {lock_file_full_path}")
        except IOError as e:
            dbg_error(f"Could not create lock file {lock_file_full_path}: {e}")
            return False # Failed to acquire lock

        quota_group = 100
        dbg_info(f"Start update data.")
        
        # Get the last trading day once before the loop
        current_last_trading_day = self.get_last_trading_update_date()

        try:
            for idx, each_product in enumerate(product_list):
                if idx % quota_group == 0:
                    self.wait_quota(quota_group)

                # Use space to avoid error message been erase.
                dbg_info(f"[{idx+1}/{product_amount}] Download code:{each_product}", prefix='\r', end=' ' * 10)
                try:
                    # When updating all data, we don't specify start_date/end_date,
                    # so it will update from last cached date to last trading day.
                    tmp_data = self.get_data(product_id = each_product, incremental_update = True,force_update = force_update)
                    
                    # Check if data was updated successfully up to the last trading day
                    if not tmp_data.empty and tmp_data.index.max().date() >= current_last_trading_day:
                        success_count += 1
                    else:
                        dbg_debug(f"Product {each_product} failed to update to {current_last_trading_day} or returned empty data.")
                except Exception as e:
                    dbg_error(f"Error updateing stock: {each_product}")
                    dbg_error(e)
                    # if the issue on quota, we wait it.
                    self.wait_quota(idx % quota_group)
                    continue

        finally:
            # Ensure the lock file is removed
            if os.path.exists(lock_file_full_path):
                try:
                    os.remove(lock_file_full_path)
                    dbg_debug(f"Lock file removed: {lock_file_full_path}")
                except OSError as e:
                    dbg_error(f"Error removing lock file {lock_file_full_path}: {e}")

        if success_count == 0 and product_amount > 0:
            dbg_error("All data updates failed.")
            return current_last_trading_day
        else:
            dbg_info(f"All {product_amount} has been update to date.", prefix='\n')
            return True
