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

    def download_data(self, product_id: str, start_date: datetime.date = None, end_date: datetime.date = None):
        yf_code = product_id + '.TW'
        dbg_info(f"Download {yf_code}")

        history_params = {}
        if start_date is not None:
            history_params['start'] = start_date.strftime('%Y-%m-%d')
        if end_date is not None:
            history_params['end'] = end_date.strftime('%Y-%m-%d')

        if not history_params: # If neither start_date nor end_date is provided
            dbg_info(f"Download {yf_code} period: max (default)")
            df = yf.Ticker(yf_code).history(period="max")
        else:
            dbg_info(f"Download {yf_code} from {history_params.get('start', 'beginning')} to {history_params.get('end', 'now')}")
            df = yf.Ticker(yf_code).history(**history_params)

        return df
    # def download_data(self, product_id: str, start_date: datetime.date = None, end_date: datetime.date = None):
    #     yf_code = ticker + '.TW'
    #     # Prioritize start_date if provided
    #     if start_date is not None:
    #         # Ensure start_date is in a format yfinance understands (YYYY-MM-DD string or datetime object)
    #         start_date_str = start_date.strftime('%Y-%m-%d') if isinstance(start_date, datetime) else start_date
    #         dbg_info(f"Download {yf_code} starting from: {start_date_str}")
    #         df = yf.Ticker(yf_code).history(start=start_date_str)
    #     # Fallback to period if start_date is not provided
    #     elif period is not None:
    #         if period == 0:
    #             period_str = 'max'
    #         else:
    #             # Ensure period is a string like '1d', '5d', '1mo', '1y', 'max' etc.
    #             period_str = str(period) # Assuming period is passed correctly formatted
    #         dbg_info(f"Download {yf_code} period: {period_str}")
    #         df = yf.Ticker(yf_code).history(period=period_str)
    #     # Default to 'max' period if neither start_date nor period is specified
    #     else:
    #         dbg_info(f"Download {yf_code} period: max (default)")
    #         df = yf.Ticker(yf_code).history(period="max")
    #
    #     return df
