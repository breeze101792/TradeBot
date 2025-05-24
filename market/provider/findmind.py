import pandas as pd
import traceback
import os
import requests

import time
from datetime import datetime

from utility.debug import *
from market.dataprovider import *

from FinMind.data import DataLoader
from FinMind.data import FinMindApi

# This still be the experimental provider. don't use it, since it's not all verfied with other trusted data.
class FindMind(DataProvider):
    NAME='findmind'
    SUPPORTED_ADJUSTED_DATA = True
    def __init__(self):
        super().__init__()
        self.token_file = "~/.findmind.key"
        self.token = None # Initialize token to None

        self._load_token() # Load token from file
        # Initialize DataLoader with the loaded token
        self.findmind = DataLoader(token=self.token)
        # self.download_data = self.fetch_adjusted_data
        self.download_data = self.fetch_adjusted_data_api

        # self.download_data = self.fetch_data

    def get_quota(self):
        safty_cnt = 100
        api = FinMindApi()
        api.login_by_token(self.token)
        remain_quota = api.api_usage_limit - api.api_usage - safty_cnt

        if remain_quota < 50:
            dbg_info('Quota less then 50')
        return remain_quota

    def _load_token(self):
        """
        Reads the FinMind API token from the specified file.
        Expands the user home directory in the file path.
        """
        token_filepath = os.path.expanduser(self.token_file)
        try:
            with open(token_filepath, 'r') as f:
                self.token = f.read().strip()
                if not self.token:
                    dbg_warning(f"FinMind token file '{token_filepath}' is empty.")
                    self.token = None # Ensure token is None if file is empty
                else:
                    dbg_debug(f"Successfully loaded FinMind token from '{token_filepath}'.")
        except FileNotFoundError:
            dbg_warning(f"FinMind token file not found at '{token_filepath}'. API calls requiring a token may fail.")
            self.token = None
        except IOError as e:
            dbg_error(f"Error reading FinMind token file '{token_filepath}': {e}")
            self.token = None
        except Exception as e:
            dbg_error(f"An unexpected error occurred while loading FinMind token: {e}")
            self.token = None

    def download_data_list(self, market: str = None, country: str = None):
        """
        Downloads a list of stocks from FinMind, mimicking twse.py structure.
        Filters by market, defaulting to 'listed' if no market is specified.
        FinMind data is specific to Taiwan.
        """
        try:
            df_delisted_info = self.findmind.taiwan_stock_delisting()

            df_info = self.findmind.taiwan_stock_info()
        except Exception as e:
            dbg_error(f"Error fetching taiwan_stock_info from FinMind: {e}")
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return pd.DataFrame()

        if df_info.empty:
            dbg_warning("No stock list data returned from FinMind.")
            return pd.DataFrame()

        product_list = []
        seen_stock_ids = set() # To track unique stock_ids

        for index, row in df_info.iterrows():
            fm_type = row.get('type')
            stock_id = row.get('stock_id')
            industry_category = row.get('industry_category')
            
            if stock_id in df_delisted_info["stock_id"].values:
                # dbg_info(f'{stock_id} is delisted.')
                continue

            # Check for duplicate stock_id
            if stock_id in seen_stock_ids:
                # BUG, there is an issue with findind, lost of data listed as duplicated.
                # dbg_warning(f"Duplicate stock_id '{stock_id}' found in FinMind data. Skipping this entry.")
                continue

            mapped_market = None
            if fm_type == 'twse':
                mapped_market = 'listed'
            elif fm_type == 'otc':
                mapped_market = 'otc'
                # Add more mappings if FinMind introduces other types like 'emerging'
            else:
                # dbg_warning(f"Unrecognized FinMind stock type: {fm_type} for {stock_id}")
                continue # Skip unrecognized types

            if industry_category == 'ETF' or industry_category == 'Index' or industry_category == '大盤' or industry_category == '存託憑證' or industry_category == '所有證券' or industry_category == 'ETN' or  industry_category == 'tpex'  :
                # NOTE. For now, ignore it.
                continue
            if stock_id.isdigit() is False:
                # print(f"{stock_id} {row}")
                continue

            # If a specific market is requested (e.g. 'listed', 'otc')
            if market:
                if mapped_market != market:
                    continue  # Skip if it doesn't match the requested market
            # If no specific market is requested, default to 'listed' (mimicking twse.py)
            elif mapped_market != 'listed':
                continue
            
            # If country parameter is provided and is not 'TW' (case-insensitive), skip
            if country and country.upper() != 'TW':
                continue

            # If mapped_market is None at this point (e.g. unrecognized fm_type and no market filter)
            if not mapped_market:
                dbg_warning(f"Skipping stock {stock_id} due to unmapped or filtered market type: {fm_type}")
                continue

            product_data = {
                "code": stock_id,
                "type": "股票",  # FinMind taiwan_stock_info lists stocks
                "name": row.get('stock_name'),
                # FIXME, this is an update date, not a start date.
                "start": row.get('date'),  # Format 'YYYY-MM-DD'
                "market": mapped_market,
                "category": row.get('industry_category'),
                "country": "TW",
            }
            product_list.append(product_data)
            seen_stock_ids.add(stock_id) # Add to set to track uniqueness
        
        df_result = pd.DataFrame(product_list)
        if not df_result.empty:
            df_result.set_index('code', inplace=True)
        return df_result

    def fetch_data(self, ticker: str, start_date: datetime.date = None, end_date: datetime.date = None):
        """
        Downloads historical stock data from FinMind.
        :param ticker: Stock ticker symbol.
        :param start_date: Datetime.date object for the start date of the data.
        :param end_date: Datetime.date object for the end date of the data.
        :return: Pandas DataFrame with historical stock data.
        """
        fm_start_date_str = (start_date if start_date else datetime(2000, 1, 1).date()).strftime('%Y-%m-%d')
        fm_end_date_str = (end_date if end_date else datetime.now().date()).strftime('%Y-%m-%d')

        dbg_trace(f"Downloading {ticker} from FinMind: {fm_start_date_str} to {fm_end_date_str}")

        try:
            df_fm = self.findmind.taiwan_stock_daily(
                stock_id=ticker,
                start_date=fm_start_date_str,
                end_date=fm_end_date_str
            )
        except Exception as e:
            dbg_error(f"Error downloading data for {ticker} from FinMind: {e}")
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return pd.DataFrame()

        if df_fm.empty:
            dbg_warning(f"No data returned from FinMind for {ticker} for the period {fm_start_date_str} to {fm_end_date_str}.")
            return pd.DataFrame()

        df_fm.rename(columns={
            'date': 'Date',
            'open': 'Open',
            'max': 'High',
            'min': 'Low',
            'close': 'Close',
            'Trading_Volume': 'Volume',
            'Trading_money': 'Turnover',
            'spread': 'Change'
        }, inplace=True)

        df_fm['Transaction'] = 0 # FinMind does not provide transaction count

        target_columns = ["Date", "Open", "High", "Low", "Close", "Volume", "Turnover", "Change", "Transaction"]
        # Ensure only existing columns are selected, in the desired order
        df_fm = df_fm[[col for col in target_columns if col in df_fm.columns]]


        if 'Date' not in df_fm.columns:
            dbg_error(f"Date column missing in data for {ticker} from FinMind.")
            return pd.DataFrame()
            
        df_fm['Date'] = pd.to_datetime(df_fm['Date'])
        df_fm.set_index('Date', inplace=True)
        
        numeric_cols = ['Open', 'High', 'Low', 'Close', 'Change']
        for col in numeric_cols:
            if col in df_fm.columns:
                df_fm[col] = pd.to_numeric(df_fm[col], errors='coerce')

        int_cols = ['Volume', 'Turnover', 'Transaction']
        for col in int_cols:
            if col in df_fm.columns:
                df_fm[col] = pd.to_numeric(df_fm[col], errors='coerce').fillna(0).astype(int)

        critical_cols_for_nan_check = ['Open', 'High', 'Low', 'Close', 'Volume']
        df_fm.dropna(subset=[col for col in critical_cols_for_nan_check if col in df_fm.columns], inplace=True)
        
        price_cols = ['Open', 'High', 'Low', 'Close']
        for col in price_cols:
            if col in df_fm.columns:
                df_fm = df_fm[df_fm[col] > 0]
        
        if 'Volume' in df_fm.columns:
            df_fm = df_fm[df_fm['Volume'] >= 0]
        
        # Final type casting for safety, for columns that survived processing
        final_dtypes = {
            "Open": float, "High": float, "Low": float, "Close": float,
            "Volume": int, "Turnover": int, "Change": float, "Transaction": int,
        }
        for col, dtype in final_dtypes.items():
            if col in df_fm.columns:
                try:
                    df_fm[col] = df_fm[col].astype(dtype)
                except Exception as e:
                    dbg_warning(f"Could not cast column {col} to {dtype} for {ticker}: {e}")

        df_fm.sort_index(inplace=True)
        return df_fm

    def fetch_dividend_result(self, symbol: str, start_date: str = '2003-05-01'):
        """
        Fetches dividend result data for a given stock from FinMind.
        :param symbol: Stock ticker symbol.
        :param start_date: Start date string in 'YYYY-MM-DD' format.
        :return: Pandas DataFrame with dividend result data.
        """
        # This method can be used for debugging or direct dividend data fetching.
        try:
            df = self.findmind.taiwan_stock_dividend_result(
                stock_id=symbol,
                start_date=start_date,
            )
            # print(f"Dividend: {df}")
            return df
        except Exception as e:
            dbg_error(f"Error fetching dividend_result for {symbol} from FinMind: {e}")
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return pd.DataFrame()

    def fetch_capital_reduction_data(self, stock_id: str, start_date: datetime):
        """
        Fetches capital reduction reference price data from FinMind.
        This data typically includes information about events like cash refunds
        that reduce a company's capital, or reverse stock splits.

        :param stock_id: The stock identifier (ticker symbol).
        :param start_date: A datetime object for the start date of the data query.
        :return: Pandas DataFrame with capital reduction data, or an empty DataFrame on error.
                 Columns include: date, stock_id, ClosingPriceonTheLastTradingDay,
                 PostReductionReferencePrice, LimitUp, LimitDown, OpeningReferencePrice,
                 ExrightReferencePrice, ReasonforCapitalReduction.
                 The 'date' column is the index and is of pd.Timestamp type.
        """
        api_url = "https://api.finmindtrade.com/api/v4/data"
        
        if not self.token:
            # dbg_warning("FinMind API token is not available.")
            # return pd.DataFrame()
            headers = {} # No auth header if no token
        else:
            # Use the token loaded from the file
            headers = {"Authorization": f"Bearer {self.token}"}
        
        params = {
            "dataset": "TaiwanStockCapitalReductionReferencePrice",
            "data_id": stock_id,
            "start_date": start_date.strftime('%Y-%m-%d'),
        }

        dbg_trace(f"Fetching capital reduction data for {stock_id} from {params['start_date']}")

        try:
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            
            data_json = response.json()
            
            if data_json.get('msg') != 'success':
                dbg_error(f"FinMind API error for capital reduction data ({stock_id}): {data_json.get('msg')}")
                return pd.DataFrame()

            df_reduction = pd.DataFrame(data_json.get('data', []))

            if df_reduction.empty:
                dbg_info(f"No capital reduction data found for {stock_id} from {params['start_date']}.")
                return pd.DataFrame()

            # Convert 'date' column to datetime and set as index
            if 'date' in df_reduction.columns:
                df_reduction['date'] = pd.to_datetime(df_reduction['date'])
                df_reduction.set_index('date', inplace=True)
                df_reduction.sort_index(inplace=True)
            else:
                dbg_warning(f"Date column missing in capital reduction data for {stock_id}.")
                # Return as is, or empty if date is critical and missing
                return df_reduction if not df_reduction.empty else pd.DataFrame()
            
            # Optional: Convert other columns to numeric if necessary, based on expected data types
            # For example:
            # numeric_cols = ['ClosingPriceonTheLastTradingDay', 'PostReductionReferencePrice', ...]
            # for col in numeric_cols:
            #     if col in df_reduction.columns:
            #         df_reduction[col] = pd.to_numeric(df_reduction[col], errors='coerce')

            # sample output.
            # date stock_id ClosingPriceonTheLastTradingDay PostReductionReferencePrice LimitUp LimitDown OpeningReferencePrice ExrightReferencePrice ReasonforCapitalReduction
            # 2022-09-19 2603 80.8 187.0 205.5 168.5 187.0 -1.0 Cash refund

            # dbg_info(f"reduction: {df_reduction}")
            return df_reduction

        except requests.exceptions.RequestException as e:
            dbg_error(f"Request error fetching capital reduction data for {stock_id}: {e}")
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return pd.DataFrame()
        except ValueError as e: # Includes JSONDecodeError
            dbg_error(f"Error decoding JSON response for capital reduction data ({stock_id}): {e}")
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return pd.DataFrame()
        except Exception as e:
            dbg_error(f"Unexpected error fetching capital reduction data for {stock_id}: {e}")
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return pd.DataFrame()

    def fetch_adjusted_data_api(self, ticker: str, start_date: datetime.date = None, end_date: datetime.date = None):
        """
        Downloads historical adjusted stock data from FinMind using the TaiwanStockPriceAdj endpoint.
        This endpoint is supposed to provide already adjusted OHLCV data.
        (This method is kept for reference; the primary adjusted data fetching now uses manual calculation).

        :param ticker: Stock ticker symbol.
        :param start_date: Datetime.date object for the start date of the data.
        :param end_date: Datetime.date object for the end date of the data.
        :return: Pandas DataFrame with adjusted historical stock data.
        """
        api_url = "https://api.finmindtrade.com/api/v4/data"

        if not self.token:
            # dbg_warning("FinMind API token is not available.")
            # return pd.DataFrame()
            headers = {} # No auth header if no token
        else:
            # Use the token loaded from the file
            headers = {"Authorization": f"Bearer {self.token}"}

        fm_start_date_str = (start_date if start_date else datetime(2000, 1, 1).date()).strftime('%Y-%m-%d')
        fm_end_date_str = (end_date if end_date else datetime.now().date()).strftime('%Y-%m-%d')

        params = {
            "dataset": "TaiwanStockPriceAdj",
            "data_id": ticker,
            "start_date": fm_start_date_str,
            "end_date": fm_end_date_str
        }

        dbg_trace(f"Fetching adjusted data for {ticker} from FinMind: {fm_start_date_str} to {fm_end_date_str}")

        try:
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)

            data_json = response.json()

            if data_json.get('msg') != 'success':
                dbg_error(f"FinMind API error for adjusted data ({ticker}): {data_json.get('msg')}")
                return pd.DataFrame()

            df_adj = pd.DataFrame(data_json.get('data', []))

            if df_adj.empty:
                dbg_warning(f"No adjusted data returned from FinMind for {ticker} for the period {fm_start_date_str} to {fm_end_date_str}.")
                return pd.DataFrame()

            # Rename columns to match the expected format
            df_adj.rename(columns={
                'date': 'Date',
                'open': 'Open',
                'max': 'High',
                'min': 'Low',
                'close': 'Close',
                'Trading_Volume': 'Volume',
                'Trading_money': 'Turnover',
                'spread': 'Change' # Note: 'spread' might not be the same as 'Change' after adjustment, but keeping for consistency with fetch_data
            }, inplace=True)

            # Add 'Transaction' column if it doesn't exist (FinMind doesn't provide it)
            if 'Transaction' not in df_adj.columns:
                 df_adj['Transaction'] = 0

            # Ensure only relevant columns are selected, in the desired order
            target_columns = ["Date", "Open", "High", "Low", "Close", "Volume", "Turnover", "Change", "Transaction"]
            df_adj = df_adj[[col for col in target_columns if col in df_adj.columns]]

            if 'Date' not in df_adj.columns:
                dbg_error(f"Date column missing in adjusted data for {ticker} from FinMind.")
                return pd.DataFrame()

            df_adj['Date'] = pd.to_datetime(df_adj['Date'])
            df_adj.set_index('Date', inplace=True)

            # Convert numeric columns, handling potential errors
            numeric_cols = ['Open', 'High', 'Low', 'Close', 'Change']
            for col in numeric_cols:
                if col in df_adj.columns:
                    df_adj[col] = pd.to_numeric(df_adj[col], errors='coerce')

            int_cols = ['Volume', 'Turnover', 'Transaction']
            for col in int_cols:
                if col in df_adj.columns:
                    df_adj[col] = pd.to_numeric(df_adj[col], errors='coerce').fillna(0).astype(int)

            # Drop rows with NaN in critical columns after conversion
            critical_cols_for_nan_check = ['Open', 'High', 'Low', 'Close', 'Volume']
            df_adj.dropna(subset=[col for col in critical_cols_for_nan_check if col in df_adj.columns], inplace=True)

            # Drop rows with non-positive prices or negative volume
            price_cols = ['Open', 'High', 'Low', 'Close']
            for col in price_cols:
                if col in df_adj.columns:
                    df_adj = df_adj[df_adj[col] > 0]

            if 'Volume' in df_adj.columns:
                df_adj = df_adj[df_adj['Volume'] >= 0]

            # Final type casting for safety
            final_dtypes = {
                "Open": float, "High": float, "Low": float, "Close": float,
                "Volume": int, "Turnover": int, "Change": float, "Transaction": int,
            }
            for col, dtype in final_dtypes.items():
                if col in df_adj.columns:
                    try:
                        df_adj[col] = df_adj[col].astype(dtype)
                    except Exception as e:
                        dbg_warning(f"Could not cast column {col} to {dtype} for {ticker} in adjusted data: {e}")

            df_adj.sort_index(inplace=True)

            # Recalculate 'Change' based on adjusted close prices for accuracy
            if 'Change' in df_adj.columns and not df_adj.empty:
                prev_close = df_adj['Close'].shift(1)
                df_adj['Change'] = df_adj['Close'] - prev_close
                if len(df_adj.index) > 0:
                    df_adj.loc[df_adj.index[0], 'Change'] = 0.0 # First day's change is 0

            return df_adj
        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
        return pd.DataFrame()

    def fetch_adjusted_data(self, ticker: str, start_date: datetime.date = None, end_date: datetime.date = None):
        """
        Downloads historical stock data from FinMind and adjusts OHLC prices for dividends and stock splits.
        The 'Close' price in the returned DataFrame is the adjusted close price.

        Methodology:
        1. Fetch raw daily stock prices for the specified period.
        2. Fetch dividend announcement data (which includes ex-dividend dates, cash dividend amounts, and stock dividend values).
           Note: FinMind's `taiwan_stock_dividend_result` uses announcement dates for its `start_date` parameter.
           The actual ex-dividend dates are in the 'date' column of the returned data.
        3. Process these announcements:
            - Filter for relevant dividend types ('息' for cash, '權' for stock).
            - Calculate cash dividend amounts and stock dividend ratios (stock dividend value / par value).
            - Create a list of dividend events, each with an ex-dividend date, cash amount, and stock ratio.
        4. Group events by ex-dividend date (to handle multiple corporate actions on the same day) and sort them in
           descending chronological order (newest to oldest). This is crucial for applying adjustments backwards in time.
        5. Iterate through the sorted dividend events:
            - For each event, select all price data *prior* to the ex-dividend date.
            - If it's a cash dividend:
                - Calculate an adjustment factor: (Price_before_ex_div - Cash_Dividend) / Price_before_ex_div.
                - Multiply historical OHLC prices by this factor.
            - If it's a stock dividend (e.g., 10% stock dividend means 0.1 new shares per old share, so stock_div_r = 0.1):
                - Calculate a price adjustment factor: 1 / (1 + stock_div_r).
                - Multiply historical OHLC prices by this factor.
                - Calculate a volume adjustment factor: (1 + stock_div_r).
                - Multiply historical Volume by this factor (or divide by the price adjustment factor).
        6. After all adjustments, round prices and recalculate the 'Change' column based on the adjusted 'Close' prices.
        Other OHLC prices (Open, High, Low) are also adjusted. Volume is adjusted for stock splits/dividends.
        :param ticker: Stock ticker symbol.
        :param start_date: Datetime.date object for the start date of the data.
        :param end_date: Datetime.date object for the end date of the data.
        :return: Pandas DataFrame with adjusted historical stock data.
        """
        # 1. Fetch daily stock data using the existing fetch_data method
        # This provides the raw, unadjusted OHLCV data.
        df_prices = self.fetch_data(ticker, start_date, end_date)
        if df_prices.empty:
            dbg_warning(f"No price data for {ticker}, cannot calculate adjusted prices.")
            return pd.DataFrame()

        actual_start_date_prices = df_prices.index.min() # The earliest date for which we have price data.
        
        # 2. Fetch dividend announcement data from FinMind.
        # The `taiwan_stock_dividend_result` endpoint provides information about ex-dividend events.
        # Its `start_date` parameter filters by announcement date, not ex-dividend date.
        # To ensure we capture all relevant ex-dividend events that might affect our price data period,
        # we fetch announcements starting from a bit earlier than our price data's start date.
        # (e.g., an announcement in December for an ex-dividend date in January).
        # Using 180 days as a buffer should be sufficient for most cases.
        dividend_announcement_start_str = (actual_start_date_prices - pd.Timedelta(days=180)).strftime('%Y-%m-%d')
        
        # Use the class's own method to fetch dividend data
        df_dividend_announcements = self.fetch_dividend_result(
            symbol=ticker,
            start_date=dividend_announcement_start_str
        )
        # fetch_dividend_result already handles exceptions and returns an empty DataFrame on error.
        # It also logs errors and potentially the DataFrame content internally via dbg_info.

        # If df_dividend_announcements is empty after the call, it means either no data was found
        # or an error occurred during fetching (which fetch_dividend_result would have logged).
        # No need to explicitly log an exception here for the fetch operation itself.

        if df_dividend_announcements.empty:
            dbg_info(f"No dividend announcements found for {ticker} for the period. Prices are effectively unadjusted or no dividends occurred.")
            return df_prices

        # 3. Process dividend announcements from FinMind into a structured list of ex-dividend events.
        # Each event will record the ex-dividend date, cash dividend amount, and stock dividend ratio.
        dividend_events = []
        par_value = 10.0 # Standard par value for Taiwanese stocks, used to calculate stock dividend ratio.

        for _, row in df_dividend_announcements.iterrows():
            # Based on the example output provided (comment lines 238-243),
            # the relevant columns are 'date' (as ex-dividend date),
            # 'stock_and_cache_dividend' (for the value),
            # and 'stock_or_cache_dividend' (for the type: '息' or '權').
            # 'date' column from FinMind's dividend_result is the ex-dividend date.
            ex_date_str = row.get('date') 
            # 'stock_and_cache_dividend' holds the NTD value of the dividend (per share for cash, total value for stock dividend per share).
            dividend_value_from_row = row.get('stock_and_cache_dividend')
            # 'stock_or_cache_dividend' indicates the type: '息' (cash) or '權' (stock rights/dividend).
            dividend_type_char = row.get('stock_or_cache_dividend')

            before_dividend_price = row.get('before_price')
            after_dividend_price = row.get('after_price')

            # Validate essential data fields from the dividend announcement.
            if pd.isna(ex_date_str) or \
               pd.isna(dividend_value_from_row) or not isinstance(dividend_value_from_row, (int, float)) or dividend_value_from_row <= 0 or \
               pd.isna(dividend_type_char):
                # dbg_trace(f"Skipping dividend row due to missing/invalid data for {ticker}: date='{ex_date_str}', value='{dividend_value_from_row}', type='{dividend_type_char}'")
                continue

            event_date = pd.to_datetime(ex_date_str) # This is the ex-dividend date.
            
            # Only consider dividend events whose ex-date falls within or after the start of our price data period.
            # Events before this date would have already been factored into older historical data not being fetched.
            if event_date < actual_start_date_prices:
                continue

            cash_div_amount = 0.0
            stock_div_r = 0.0

            # Original types: '息' (cash), '權' (stock)
            # New types from logs: '除息' (cash), '除權' (stock), '除權息' (cash and stock)

            if dividend_type_char == '息' or dividend_type_char == '除息': # Cash dividend
                cash_div_amount = float(dividend_value_from_row)
            elif dividend_type_char == '權' or dividend_type_char == '除權': # Stock dividend
                # 'stock_and_cache_dividend' for '權' or '除權' is the NTD value of stock dividend per share.
                # we use dividend_value_from_row / before_dividend_price to get stock ratio. it'll be used for later calc.
                stock_div_r = float(dividend_value_from_row) / before_dividend_price
                # dbg_info(f"{dividend_value_from_row}")
            elif dividend_type_char == '除權息' or dividend_type_char == '權息': # Both cash and stock
                # For '除權息' type, we assume 'stock_and_cache_dividend' represents the CASH portion.
                # This is supported by the observation that (before_price - after_price) often equals this value.
                # If there's a stock portion for this ex-dividend event, FinMind should provide it
                # in a separate row (e.g., type '權' or '除權') for the same ex-date.
                # The groupby operation later will sum cash_div and stock_div_ratio if multiple rows exist for the same date.
                cash_div_amount = float(dividend_value_from_row)
                dbg_trace(f"Interpreting '除權息' event for {ticker} on {ex_date_str} with value {dividend_value_from_row} as cash dividend component. "
                          f"Stock component, if any, should be in a separate '權' or '除權' row for the same date.")
            else:
                dbg_warning(f"Unknown dividend type '{dividend_type_char}' for {ticker} on ex-date {ex_date_str}. Row: {row.to_dict()}")
                continue # Skip unknown types
            
            # Append event if there's a valid dividend (either cash or stock)
            if cash_div_amount > 0 or stock_div_r > 0:
                dividend_events.append({
                    'date': event_date, 
                    'cash_div': cash_div_amount, 
                    'stock_div_ratio': stock_div_r
                })

        if not dividend_events:
            dbg_info(f"No relevant dividend events found for {ticker} impacting the price data period.")
            return df_prices

        # Combine dividend events and capital reduction events
        all_events = [] # List to hold all processed event dictionaries

        # Process Dividend Events (already in dividend_events list)
        for div_event in dividend_events:
            if div_event.get('cash_div', 0) > 0:
                all_events.append({
                    'date': div_event['date'],
                    'type': 'cash_dividend',
                    'cash_amount': div_event['cash_div']
                })
            if div_event.get('stock_div_ratio', 0) > 0:
                 all_events.append({
                    'date': div_event['date'],
                    'type': 'stock_dividend',
                    'stock_ratio': div_event['stock_div_ratio']
                })

        # Fetch and Process Capital Reduction Events
        df_reduction = self.fetch_capital_reduction_data(stock_id=ticker, start_date=actual_start_date_prices)
        if not df_reduction.empty:
            for _, reduction_row in df_reduction.iterrows():
                event_date = reduction_row.name # Index is 'date' (pd.Timestamp)
                
                if event_date < actual_start_date_prices:
                    continue

                price_before_reduction = reduction_row.get('ClosingPriceonTheLastTradingDay')
                price_after_reduction = reduction_row.get('PostReductionReferencePrice')

                if pd.isna(price_before_reduction) or pd.isna(price_after_reduction) or \
                   price_before_reduction <= 0:
                    dbg_warning(f"Skipping capital reduction event for {ticker} on {event_date.strftime('%Y-%m-%d')} due to missing/invalid prices: "
                                f"Before={price_before_reduction}, After={price_after_reduction}")
                    continue
                
                if price_after_reduction <= 0:
                    dbg_warning(f"Capital reduction event for {ticker} on {event_date.strftime('%Y-%m-%d')} has PostReductionReferencePrice <= 0 ({price_after_reduction}). "
                                f"This specific event's adjustment will be skipped.")
                    continue
                
                price_adj_factor = price_after_reduction / price_before_reduction
                volume_adj_factor = price_before_reduction / price_after_reduction
                
                all_events.append({
                    'date': event_date,
                    'type': 'capital_reduction',
                    'price_adj_factor': price_adj_factor,
                    'volume_adj_factor': volume_adj_factor
                })

        if not all_events:
            dbg_info(f"No dividend or capital reduction events found for {ticker} impacting the price data period.")
            # Recalculate 'Change' for unadjusted prices if it exists, then return
            if 'Change' in df_prices.columns and not df_prices.empty:
                prev_close = df_prices['Close'].shift(1)
                df_prices['Change'] = df_prices['Close'] - prev_close
                if len(df_prices.index) > 0:
                    df_prices.loc[df_prices.index[0], 'Change'] = 0.0
            return df_prices

        all_events_df = pd.DataFrame(all_events)
        all_events_df.sort_values(by='date', ascending=False, inplace=True)

        ohlc_cols = ['Open', 'High', 'Low', 'Close']
        made_volume_float = False # Flag to track if Volume dtype was changed to float

        # 5. Iterate through sorted events and apply adjustments
        for _, event_row in all_events_df.iterrows():
            ex_date = event_row['date']
            event_type = event_row['type']

            idx_loc_ex_date = df_prices.index.searchsorted(ex_date, side='left')

            if idx_loc_ex_date == 0:
                dbg_trace(f"Event date {ex_date.strftime('%Y-%m-%d')} for {ticker} (type: {event_type}) is at or before start of price data. Skipping adjustment.")
                continue
            
            target_rows_index = df_prices.index[:idx_loc_ex_date]
            if target_rows_index.empty:
                continue

            if event_type == 'cash_dividend':
                cash_div = event_row['cash_amount']
                if cash_div > 0:
                    close_on_prev_day = df_prices.loc[df_prices.index[idx_loc_ex_date - 1], 'Close']
                    adj_ratio_cash = None
                    if close_on_prev_day > 0 and close_on_prev_day > cash_div:
                        adj_ratio_cash = (close_on_prev_day - cash_div) / close_on_prev_day
                    elif close_on_prev_day > 0 and close_on_prev_day <= cash_div:
                        dbg_warning(f"Cash dividend ({cash_div}) for {ticker} on {ex_date.strftime('%Y-%m-%d')} "
                                    f"is >= Closing price on previous day ({close_on_prev_day}). Setting adj_ratio to small value.")
                        adj_ratio_cash = 0.0001 
                    else:
                        dbg_warning(f"Invalid prev_day_close ({close_on_prev_day}) for cash dividend adjustment for {ticker} on {ex_date.strftime('%Y-%m-%d')}.")

                    if adj_ratio_cash is not None:
                        for col_name in ohlc_cols:
                            df_prices.loc[target_rows_index, col_name] *= adj_ratio_cash
            
            elif event_type == 'stock_dividend':
                stock_div_r = event_row['stock_ratio']
                if stock_div_r > 0:
                    adj_ratio_price = 1.0 / (1.0 + stock_div_r)
                    adj_ratio_volume = 1.0 + stock_div_r

                    for col_name in ohlc_cols:
                        df_prices.loc[target_rows_index, col_name] *= adj_ratio_price
                    
                    if 'Volume' in df_prices.columns:
                        if not made_volume_float and df_prices['Volume'].dtype != float:
                            df_prices['Volume'] = df_prices['Volume'].astype(float)
                            made_volume_float = True
                        df_prices.loc[target_rows_index, 'Volume'] *= adj_ratio_volume
            
            elif event_type == 'capital_reduction':
                price_adj = event_row['price_adj_factor']
                volume_adj = event_row['volume_adj_factor']

                for col_name in ohlc_cols:
                    df_prices.loc[target_rows_index, col_name] *= price_adj
                
                if 'Volume' in df_prices.columns:
                    if not made_volume_float and df_prices['Volume'].dtype != float:
                        df_prices['Volume'] = df_prices['Volume'].astype(float)
                        made_volume_float = True
                    df_prices.loc[target_rows_index, 'Volume'] *= volume_adj

        # 6. Post-Adjustment Processing
        if 'Volume' in df_prices.columns and made_volume_float:
            df_prices['Volume'] = df_prices['Volume'].round().astype(int)

        for col_name in ohlc_cols:
            if col_name in df_prices.columns:
                df_prices[col_name] = df_prices[col_name].round(4) 

        if 'Change' in df_prices.columns:
            prev_close = df_prices['Close'].shift(1)
            df_prices['Change'] = df_prices['Close'] - prev_close
            if not df_prices.empty and len(df_prices.index) > 0:
                 df_prices.loc[df_prices.index[0], 'Change'] = 0.0

        return df_prices


if __name__ == "__main__":
    def compare_and_show_different(df_old, df_new, days_before=15, days_after=15):
        """
        Compares two DataFrames and shows the first row where they differ.
        """
        if df_old.equals(df_new):
            print("\nDataFrames are identical.")
            return

        # Find the first differing row
        # Ensure columns are in the same order for comparison
        if not df_old.columns.equals(df_new.columns):
             print("\nDataFrames have different columns. Cannot compare.")
             print("df_old columns:", df_old.columns.tolist())
             print("df_new columns:", df_new.columns.tolist())
             return

        # Align indices before comparison
        common_index = df_old.index.intersection(df_new.index)
        df_old_aligned = df_old.loc[common_index]
        df_new_aligned = df_new.loc[common_index]

        # Check for rows present in one but not the other
        diff_index_old_only = df_old.index.difference(df_new.index)
        diff_index_new_only = df_new.index.difference(df_old.index)

        if not diff_index_old_only.empty:
            print(f"\nFirst index present only in df_old: {diff_index_old_only[0]}")
            print("Row from df_old:")
            print(df_old.loc[[diff_index_old_only[0]]])
            return # Show the first difference found

        if not diff_index_new_only.empty:
            print(f"\nFirst index present only in df_new: {diff_index_new_only[0]}")
            print("Row from df_new:")
            print(df_new.loc[[diff_index_new_only[0]]])
            return # Show the first difference found

        # Compare aligned data
        comparison_result = df_old_aligned.ne(df_new_aligned)
        
        # Find the index of the first row with any difference
        first_diff_row_index = comparison_result.any(axis=1).idxmax()

        if pd.isna(first_diff_row_index):
             print("\nDataFrames are identical (after alignment).") # Should not happen if equals() was false, but as a safeguard
             return

        print(f"\nFirst differing row at index: {first_diff_row_index}")
        print("\nRow from df_old:")
        print(df_old.loc[[first_diff_row_index]])
        print("\nRow from df_new:")
        print(df_new.loc[[first_diff_row_index]])

        # Optional: Show which columns differ in this row
        diff_columns = comparison_result.loc[first_diff_row_index][comparison_result.loc[first_diff_row_index]].index.tolist()
        print(f"\nDiffering columns in this row: {diff_columns}")

        # --- Add code to show data around the first differing row ---
        try:
            first_diff_date = first_diff_row_index # The index is already a datetime
            start_slice_dt = first_diff_date - pd.Timedelta(days=days_before)
            end_slice_dt = first_diff_date + pd.Timedelta(days=days_after)

            print(f"\nShowing data around the first differing row ({first_diff_date.strftime('%Y-%m-%d')}):")
            print(f"Slice range: {start_slice_dt.strftime('%Y-%m-%d')} to {end_slice_dt.strftime('%Y-%m-%d')}")

            print("\nOriginal data (df_old) slice:")
            try:
                slice_old = df_old.loc[start_slice_dt:end_slice_dt]
                if not slice_old.empty:
                    print(slice_old)
                else:
                    print("No original data in this slice range.")
            except KeyError:
                 print("Could not slice original data (KeyError).")

            print("\nAdjusted data (df_new) slice:")
            try:
                slice_new = df_new.loc[start_slice_dt:end_slice_dt]
                if not slice_new.empty:
                    print(slice_new)
                else:
                    print("No adjusted data in this slice range.")
            except KeyError:
                print("Could not slice adjusted data (KeyError).")

        except Exception as e:
            dbg_error(f"Error displaying slice around first differing row: {e}")
        # --- End of added code ---


    def compare_days_around(df_old, df_new, ticker_symbol, target_date_str_arg, days_before=15, days_after=15):
        """
        Compares slices of two DataFrames (df_old, df_new) around a target date.
        df_old: DataFrame containing original data.
        df_new: DataFrame containing adjusted (or new) data.
        ticker_symbol: The stock ticker symbol (for print statements).
        target_date_str_arg: The target event date string ('YYYY-MM-DD').
        days_before: Number of days before target_date_str_arg to start the slice.
        days_after: Number of days after target_date_str_arg to end the slice.
        """
        try:
            target_dt = pd.to_datetime(target_date_str_arg)
        except Exception as e:
            print(f"Error converting target_date_str_arg '{target_date_str_arg}' to datetime: {e}")
            return

        start_slice_dt = target_dt - pd.Timedelta(days=days_before)
        end_slice_dt = target_dt + pd.Timedelta(days=days_after)

        start_slice_date_str = start_slice_dt.strftime('%Y-%m-%d')
        end_slice_date_str = end_slice_dt.strftime('%Y-%m-%d')

        print(f"\nComparing data for ticker {ticker_symbol} around event date {target_date_str_arg}")
        print(f"Displaying slice from {start_slice_date_str} to {end_slice_date_str}:")

        print(f"\nOriginal data (df_old) for {ticker_symbol}:")
        if df_old.empty:
            print("Original data (df_old) is empty.")
        else:
            try:
                if not isinstance(df_old.index, pd.DatetimeIndex):
                    print("Warning: df_old index is not DatetimeIndex. Slicing might fail or be incorrect.")
                
                date_slice_old = df_old.loc[start_slice_date_str:end_slice_date_str]
                if not date_slice_old.empty:
                    print(date_slice_old)
                else:
                    print(f"No original data found in the range {start_slice_date_str} to {end_slice_date_str}.")
            except KeyError:
                print(f"Could not slice original data for dates {start_slice_date_str} to {end_slice_date_str} (KeyError).")
                print("Consider checking if the dates exist and the DataFrame index is sorted.")
            except Exception as e:
                print(f"Error slicing original data: {e}")
        
        print(f"\nAdjusted data (df_new) for {ticker_symbol}:")
        if df_new.empty:
            print("Adjusted data (df_new) is empty.")
        else:
            try:
                if not isinstance(df_new.index, pd.DatetimeIndex):
                    print("Warning: df_new index is not DatetimeIndex. Slicing might fail or be incorrect.")

                date_slice_new = df_new.loc[start_slice_date_str:end_slice_date_str]
                if not date_slice_new.empty:
                    print(date_slice_new)
                else:
                    print(f"No adjusted data found in the range {start_slice_date_str} to {end_slice_date_str}.")
            except KeyError:
                print(f"Could not slice adjusted data for dates {start_slice_date_str} to {end_slice_date_str} (KeyError).")
                print("Consider checking if the dates exist and the DataFrame index is sorted.")
            except Exception as e:
                print(f"Error slicing adjusted data: {e}")

    fm = FindMind()
    
    # Example usage for fetch_dividend_result (can be used for debugging)
    # fm.fetch_dividend_result(symbol='2330', start_date='2020-01-01')

    # Example usage for fetch_adjusted_data:
    ticker_to_test = '2881' # Fuban
    # Define start and end dates for testing
    test_start_date_2881 = datetime(2023, 1, 1).date()
    test_end_date_2881 = datetime.now().date()

    print(f"\nFetching original and adjusted data for {ticker_to_test} from {test_start_date_2881.strftime('%Y-%m-%d')} to {test_end_date_2881.strftime('%Y-%m-%d')}...")
    df_adj_period_2881 = fm.fetch_adjusted_data(ticker=ticker_to_test, start_date=test_start_date_2881, end_date=test_end_date_2881)
    df_ori_data_2881 = fm.fetch_data(ticker=ticker_to_test, start_date=test_start_date_2881, end_date=test_end_date_2881) # Fetch original data

    if not df_adj_period_2881.empty and not df_ori_data_2881.empty:
        print(f"\nOverview of fetched data for {ticker_to_test}:")
        # print(f"Original data for {ticker_to_test} - Head:")
        # print(df_ori_data_2881.head())
        # print(f"Adjusted data for {ticker_to_test} - Head:")
        # print(df_adj_period_2881.head())

        # Event for '2881' (Fubon) - Ex-dividend date 2023-07-20
        target_date_2881_str = '2024-09-09'
        compare_days_around(df_old=df_ori_data_2881, 
                              df_new=df_adj_period_2881, 
                              ticker_symbol=ticker_to_test, 
                              target_date_str_arg=target_date_2881_str, 
                              days_before=5, 
                              days_after=5)
        # debug early return.

        # Event for '2881' (Fubon) - Ex-dividend date 2023-07-20
        target_date_2881_str = '2024-07-19'
        compare_days_around(df_old=df_ori_data_2881, 
                              df_new=df_adj_period_2881, 
                              ticker_symbol=ticker_to_test, 
                              target_date_str_arg=target_date_2881_str, 
                              days_before=5, 
                              days_after=5)
    elif df_ori_data_2881.empty and df_adj_period_2881.empty:
        print(f"Neither original nor adjusted data returned for {ticker_to_test} with start_date={test_start_date_2881} and end_date={test_end_date_2881}.")
    elif df_ori_data_2881.empty:
        print(f"No original data returned for {ticker_to_test} with start_date={test_start_date_2881} and end_date={test_end_date_2881}.")
    elif df_adj_period_2881.empty:
        print(f"No adjusted data returned for {ticker_to_test} with start_date={test_start_date_2881} and end_date={test_end_date_2881}.")

    # Test for '8069'
    ticker_to_test_8069 = '8069'
    start_date_8069 = datetime(1995, 1, 1).date() # Fetching a long period
    end_date_8069 = datetime.now().date()
    print(f"\nFetching original and adjusted data for {ticker_to_test_8069} from {start_date_8069.strftime('%Y-%m-%d')} to {end_date_8069.strftime('%Y-%m-%d')}...")
    df_adj_data_8069 = fm.fetch_adjusted_data(ticker=ticker_to_test_8069, start_date=start_date_8069, end_date=end_date_8069)
    df_ori_data_8069 = fm.fetch_data(ticker=ticker_to_test_8069, start_date=start_date_8069, end_date=end_date_8069)

    if not df_adj_data_8069.empty and not df_ori_data_8069.empty:
        print(f"\nOverview of fetched data for {ticker_to_test_8069}:")
        # print(f"Original data for {ticker_to_test_8069} - Head:")
        # print(df_ori_data_8069.head())
        # print(f"Adjusted data for {ticker_to_test_8069} - Head:")
        # print(df_adj_data_8069.head())
        
        # Arbitrary recent date for '8069' for comparison
        target_date_8069_str = '2023-09-01' 
        compare_days_around(df_old=df_ori_data_8069, 
                              df_new=df_adj_data_8069, 
                              ticker_symbol=ticker_to_test_8069, 
                              target_date_str_arg=target_date_8069_str, 
                              days_before=5, 
                              days_after=5)
    elif df_ori_data_8069.empty and df_adj_data_8069.empty:
        print(f"Neither original nor adjusted data returned for {ticker_to_test_8069} with start_date {start_date_8069.strftime('%Y-%m-%d')} and end_date {end_date_8069.strftime('%Y-%m-%d')}.")
    elif df_ori_data_8069.empty:
        print(f"No original data returned for {ticker_to_test_8069} with start_date {start_date_8069.strftime('%Y-%m-%d')} and end_date {end_date_8069.strftime('%Y-%m-%d')}.")
    elif df_adj_data_8069.empty:
        print(f"No adjusted data returned for {ticker_to_test_8069} with start_date {start_date_8069.strftime('%Y-%m-%d')} and end_date {end_date_8069.strftime('%Y-%m-%d')}.")

    # Example usage for fetch_capital_reduction_data:
    # Note: Capital reduction events are less frequent than dividends.
    # You might need to find a stock and date range known to have such an event.
    # For example, '2498' (HTC) had a capital reduction around 2018-10-08.
    # '6271' (同欣電) had one around 2019-09-30
    # ticker_reduction_test = '6271' 
    ticker_reduction_test = '2603' 
    # We need to fetch data starting from *before* the event date to see it.
    start_date_reduction_test = datetime(2019, 9, 1) 
    print(f"\nFetching capital reduction data for {ticker_reduction_test} from {start_date_reduction_test.strftime('%Y-%m-%d')}...")
    df_reduction = fm.fetch_capital_reduction_data(stock_id=ticker_reduction_test, start_date=start_date_reduction_test)
    if not df_reduction.empty:
        print(f"Capital reduction data for {ticker_reduction_test} (from {start_date_reduction_test.strftime('%Y-%m-%d')}):")
        print(df_reduction.head())
        if len(df_reduction) > 5:
            print("...")
            print(df_reduction.tail())
    else:
        print(f"No capital reduction data returned for {ticker_reduction_test} from {start_date_reduction_test.strftime('%Y-%m-%d')}.")

    # integration test.
    # Test with a stock known for significant dividends/splits, e.g., '2603' (Evergreen Marine)
    ticker_evt_test = '2603'
    # Define start and end dates for testing
    integration_test_start_date = datetime(2020, 1, 1).date() # Ensure relevant events are covered
    integration_test_end_date = datetime.now().date()
    print(f"\nFetching original and adjusted data for {ticker_evt_test} from {integration_test_start_date.strftime('%Y-%m-%d')} to {integration_test_end_date.strftime('%Y-%m-%d')}...")
    df_adj_evt = fm.fetch_adjusted_data(ticker=ticker_evt_test, start_date=integration_test_start_date, end_date=integration_test_end_date)
    df_evt = fm.fetch_data(ticker=ticker_evt_test, start_date=integration_test_start_date, end_date=integration_test_end_date)
    if not df_adj_evt.empty and not df_evt.empty:
        print(f"\nOverview of fetched data for {ticker_evt_test}:")
        # print("Original data (df_evt) - Head:")
        # print(df_evt.head())
        # print("\nAdjusted data (df_adj_evt) - Head:")
        # print(df_adj_evt.head())
        
        # Event 1: Capital Reduction for '2603'
        # Known event date: 2022-09-19 (Cash refund from API example in fetch_capital_reduction_data)
        target_date_reduction_str = '2022-09-19'
        # Window to match original example: '2022-09-01' to '2022-09-30'
        # days_before = 19 (target day) - 1 (start day) = 18
        # days_after = 30 (end day) - 19 (target day) = 11
        compare_days_around(df_old=df_evt, 
                              df_new=df_adj_evt, 
                              ticker_symbol=ticker_evt_test, 
                              target_date_str_arg=target_date_reduction_str, 
                              days_before=18, 
                              days_after=11)

        # Event 2: Dividend for '2603'
        # Example ex-dividend date for '2603' from FinMind: 2023-06-29 (Cash Dividend: 70.0)
        target_date_dividend_str = '2023-06-29' 
        # Example window: approx. 2 weeks before and 2 weeks after (e.g., 2023-06-15 to 2023-07-13)
        # days_before = 14 (target_date_dividend_str is 29th, 29-14 = 15th)
        # days_after = 14 (target_date_dividend_str is 29th, 29+14 = 13th of next month)
        compare_days_around(df_old=df_evt, 
                              df_new=df_adj_evt, 
                              ticker_symbol=ticker_evt_test, 
                              target_date_str_arg=target_date_dividend_str, 
                              days_before=14, 
                              days_after=14)

        compare_days_around(df_old=df_evt, 
                              df_new=df_adj_evt, 
                              ticker_symbol=ticker_evt_test, 
                              target_date_str_arg=target_date_reduction_str, 
                              days_before=18, 
                              days_after=11)

    elif df_evt.empty and df_adj_evt.empty:
        print(f"Neither original (df_evt) nor adjusted (df_adj_evt) data returned for {ticker_evt_test} with start_date={integration_test_start_date} and end_date={integration_test_end_date}.")
    elif df_evt.empty:
        print(f"No original data (df_evt) returned for {ticker_evt_test} with start_date={integration_test_start_date} and end_date={integration_test_end_date}. Cannot perform full comparison.")
        if not df_adj_evt.empty: # If adjusted data exists, show its head
            print("\nAdjusted data (df_adj_evt) - Head:")
            print(df_adj_evt.head())
    elif df_adj_evt.empty:
        print(f"No adjusted data (df_adj_evt) returned for {ticker_evt_test} with start_date={integration_test_start_date} and end_date={integration_test_end_date}. Cannot perform full comparison.")
        if not df_evt.empty: # If original data exists, show its head
            print("\nOriginal data (df_evt) - Head:")
            print(df_evt.head())



