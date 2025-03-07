import yfinance as yf
import pandas as pd
import traceback

from datetime import datetime

class Yahoo:
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

    def get_ticker(ticker: str, start_date: str = None, end_date: str = None, period: str = None):
        # ticker = "8069.TWO"  # name from Yahoo Finance
        # start_date = "2018-01-01"
        # end_date = "2025-01-01"
        ticker_local_path = './data'
        ticker_local_file = ticker + ".csv"

        # Download stock data
        df = load_from_csv(ticker_local_file, 'Date', folder=ticker_local_path)
        if df is None:
            # df = yf.download(ticker, start=start_date, end=end_date, multi_level_index=False)
            df = yf.Ticker(ticker).history(period="max")
            save_to_csv(df, ticker_local_file, folder=ticker_local_path)

        # Check if data download ok
        if df.empty:
            raise ValueError("Fail to download data from Yahoo Finance, Please check your sotkc id or net work connection.")
        # else:
        #     print("Data download successfully！Showing first few lines：")
        #     print(df.head())
        return df
