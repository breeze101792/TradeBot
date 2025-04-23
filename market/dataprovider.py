import pandas as pd
import traceback
import os

from datetime import datetime, timedelta

from utility.debug import *

class DataProvider:
    NAME = 'provider'
    def __init__(self):
        self.cache_data_name = f'./{self.NAME}'
        self.cache_data_root_path = './.data'
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

    def download_data(self, product_id: str, start_date: str = None, period: str = None):
        dbg_error("Function not impl.")
        raise

    def download_data_list(self, market: str = None, country: str = None):
        dbg_error("Function not impl.")
        raise

    def get_data_list_filtered(self, market: str = None, country: str = None):
        return self.download_data_list(market = market, country = country)

    def get_data_list(self, market: str = None, country: str = None):
        return self.download_data_list(market = market, country = country)

    def get_data(self, product_id: str, period: str = None, force_update: bool = False):
        ticker_local_file = product_id.__str__() + ".csv"
        ticker_local_path = f"{self.cache_data_root_path}/{self.cache_data_name}"
        today = datetime.now()

        # Load existing data
        df = self.load_from_csv(ticker_local_file, 'Date', folder=ticker_local_path)
        
        # Check if we need to update (missing data or forced update)
        needs_update = force_update or df is None
        last_date = None
        last_trading_day = None
        if df is not None:
            if not df.empty: # Check if DataFrame is not empty
                try:
                    # Attempt to get the latest date from the index
                    last_date = df.index.max().date()
                    # Check if there is new data on the market.
                    last_trading_day = datetime.now().replace(hour=13, minute=40, second=0, microsecond=0)

                    while last_trading_day.weekday() >= 5:
                        last_trading_day -= timedelta(days=1)

                    if last_date < last_trading_day.date() and datetime.now() >= last_trading_day:
                        needs_update = True
                except Exception as e:
                    dbg_error(f"Error getting max date from index for {product_id}: {e}")
                    # If we can't get the last date, assume an update is needed
                    needs_update = True
            else:
                # DataFrame loaded but is empty, definitely needs update
                dbg_info(f"Loaded DataFrame for {product_id} is empty.")
                needs_update = True

        if needs_update:
            dbg_info(f'Update {product_id} info, from {last_date} to {last_trading_day.date()}')
            # Download new data
            new_df = self.download_data(product_id, start_date = last_date)
            if not new_df.empty:
                if df is not None:
                    # Merge old and new data, keeping the most recent
                    df = pd.concat([df, new_df]).drop_duplicates(keep='last')
                else:
                    df = new_df
                self.save_to_csv(df, ticker_local_file, folder=ticker_local_path)
        else:
            dbg_debug(f"DataFrame loaded from {ticker_local_file}")

        # Ensure df is not None before checking if it's empty
        if df is None or df.empty:
             dbg_error(f"No data available for {product_id} after attempting load/download.")
             # Optionally raise an error or return an empty DataFrame
             # raise ValueError(f"No data available for {product_id}.")
             return pd.DataFrame() # Return empty DataFrame instead of raising error immediately

        return df
