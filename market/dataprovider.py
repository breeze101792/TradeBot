import pandas as pd
import traceback
import os

from datetime import datetime

from utility.debug import *

class DataProvider:
    ticker_local_path = './data'
    def __init__(self):
        pass
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
        print(f"DataFrame saved to {file_path}")

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

    def download_data(self, product_id: str, period: str = None):
        dbg_error("Function not impl.")
        pass

    def download_data_list(self, market: str = None, country: str = None):
        dbg_error("Function not impl.")
        pass

    def get_data_list(self, market: str = None, country: str = None, force_update: bool = False):
        return self.download_data_list(market = market, country = country)

    def get_data(self, product_id: str, period: str = None, force_update: bool = False):
        ticker_local_file = product_id.__str__() + ".csv"

        # Download stock data
        df = self.load_from_csv(ticker_local_file, 'Date', folder=self.ticker_local_path)
        if df is None or force_update:
            df = self.download_data(product_id)
            if not df.empty:
                self.save_to_csv(df, ticker_local_file, folder=self.ticker_local_path)
        else:
            dbg_debug(f"DataFrame loaded from {ticker_local_file}")

        # Check if data download ok
        if df.empty:
            raise ValueError("Fail to download data, Please check your sotkc id or network connection.")
        # else:
        #     print("Data download successfully！Showing first few lines：")
        #     print(df.head())
        return df
