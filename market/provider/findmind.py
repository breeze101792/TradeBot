import pandas as pd
import traceback
import os
import requests

import time
from datetime import datetime

from utility.debug import *
from market.dataprovider import *

from FinMind.data import DataLoader

class FindMind(DataProvider):
    NAME='findmind'
    def __init__(self):
        super().__init__()
        self.token = None
        self.findmind = DataLoader()
        # self.download_data = self.fetch_adjusted_data
        self.download_data = self.fetch_data
    def download_data_list(self, market: str = None, country: str = None):
        """
        Downloads a list of stocks from FinMind, mimicking twse.py structure.
        Filters by market, defaulting to 'listed' if no market is specified.
        FinMind data is specific to Taiwan.
        """
        try:
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
        for index, row in df_info.iterrows():
            fm_type = row.get('type')
            stock_id = row.get('stock_id')
            
            mapped_market = None
            if fm_type == 'twse':
                mapped_market = 'listed'
            elif fm_type == 'otc':
                mapped_market = 'otc'
            # Add more mappings if FinMind introduces other types like 'emerging'
            # else:
            #     dbg_warning(f"Unrecognized FinMind stock type: {fm_type} for {stock_id}")
            #     continue # Skip unrecognized types

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
                "start": row.get('date'),  # Format 'YYYY-MM-DD'
                "market": mapped_market,
                "category": row.get('industry_category'),
                "country": "TW",
            }
            product_list.append(product_data)
        
        df_result = pd.DataFrame(product_list)
        return df_result

    def fetch_data(self, ticker: str, start_date: datetime = None, period: int = None):
        """
        Downloads historical stock data from FinMind.
        :param ticker: Stock ticker symbol.
        :param start_date: Datetime object for the start date of the data.
        :param period: Integer representing number of years of data to fetch.
                       If period is 0, fetches all available data from FinMind (typically from 2000-01-01).
                       If start_date is provided, period is ignored.
                       If neither is provided, defaults to all available data.
        :return: Pandas DataFrame with historical stock data.
        """
        fm_start_date_str = None
        fm_end_date_str = datetime.now().strftime('%Y-%m-%d')

        if start_date:
            fm_start_date_str = start_date.strftime('%Y-%m-%d')
        elif period is not None:
            if period == 0:
                fm_start_date_str = '2000-01-01'  # FinMind data generally available from this date
            else:
                calculated_start_date = datetime.now() - pd.DateOffset(years=period)
                fm_start_date_str = calculated_start_date.strftime('%Y-%m-%d')
        else:
            # Default: fetch all available data if neither start_date nor period is specified
            fm_start_date_str = '2000-01-01'

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
            # dbg_info(f"Dividend result for {symbol} from {start_date}:") # Can be verbose
            # dbg_info(df.head())
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
            headers = {}
        else:
            headers = {"Authorization": f"Bearer {self.findmind.token}"}
        
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

    def fetch_adjusted_data(self, ticker: str, start_date: datetime = None, period: int = None):
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
        :param start_date: Datetime object for the start date of the data.
        :param period: Integer representing number of years of data to fetch.
                       If period is 0, fetches all available data from FinMind.
                       If start_date is provided, period is ignored.
                       If neither is provided, defaults to all available data.
        :return: Pandas DataFrame with adjusted historical stock data.
        """
        # 1. Fetch daily stock data using the existing fetch_data method
        # This provides the raw, unadjusted OHLCV data.
        df_prices = self.fetch_data(ticker, start_date, period)
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
        
        try:
            df_dividend_announcements = self.findmind.taiwan_stock_dividend_result(
                stock_id=ticker,
                start_date=dividend_announcement_start_str,
                # end_date can be omitted to get all up to the latest
            )
            # date stock_id  before_price  after_price  stock_and_cache_dividend stock_or_cache_dividend  max_price  min_price  open_price  reference_price
            # 0  2022-07-27     2881          59.2        55.70                      3.50                       息       61.2      50.20        55.7            55.70
            # 1  2022-09-22     2881          56.5        53.80                      2.69                       權       59.1      48.45        53.8            53.80
            # 2  2023-07-20     2881          64.8        63.30                      1.50                       息       69.6      57.00        63.3            63.30
            # 3  2023-09-04     2881          64.8        61.71                      3.09                       權       67.8      55.60        61.7            61.71
            # 4  2024-07-19     2881          89.9        87.40                      2.50                       息       96.1      78.70        87.4            87.40
            # 5  2024-09-09     2881          92.5        88.09                      4.40                       權       96.8      79.30        88.1            88.09
            # dbg_info(df_dividend_announcements) # Can be verbose, uncomment for debugging dividend data
        except Exception as e:
            dbg_error(f"Error fetching dividend_result for {ticker} from FinMind: {e}")
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            dbg_warning(f"Proceeding with unadjusted prices for {ticker} due to dividend fetch error.")
            return df_prices # Return unadjusted prices if dividend data fetch fails.

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
                # Example: 1 NTD stock dividend per share, with par value 10 NTD, means 0.1 new shares per original share.
                # So, stock_div_r = 0.1 (i.e., a 10% stock dividend).
                stock_div_r = float(dividend_value_from_row) / par_value
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

        # dbg_info(dividend_events) # Can be verbose, uncomment for debugging processed events
        df_events = pd.DataFrame(dividend_events)
        
        # 4. Group and Sort Events
        # Group by ex-dividend date ('date') in case multiple corporate actions (e.g., cash and stock dividend) occur on the same day.
        # Sum cash dividends and stock dividend ratios for the same ex-date.
        grouped_events = df_events.groupby('date').agg(
            cash_div=('cash_div', 'sum'),
            stock_div_ratio=('stock_div_ratio', 'sum') 
        ).reset_index()
        
        # Sort events by ex-dividend date in descending order (newest to oldest).
        # Adjustments must be applied backwards in time: adjust for the most recent dividend first, then the next recent, and so on.
        grouped_events.sort_values(by='date', ascending=False, inplace=True)

        ohlc_cols = ['Open', 'High', 'Low', 'Close']
        any_stock_dividend_applied = False # Flag to track if volume needs int conversion later.

        # 5. Iterate through the sorted (descending by date) dividend events and apply adjustments to historical prices.
        for _, event_row in grouped_events.iterrows():
            ex_date = event_row['date'] # The ex-dividend date for the current event.
            cash_div = event_row['cash_div']
            stock_div_r = event_row['stock_div_ratio'] 

            # Find the index location of the ex-dividend date in our price DataFrame.
            # `searchsorted` finds where `ex_date` would be inserted to maintain order.
            # `side='left'` means if `ex_date` exists, its index is returned.
            idx_loc_ex_date = df_prices.index.searchsorted(ex_date, side='left')

            # If the ex-dividend date is before or at the very start of our price data,
            # it means this dividend's effect is on data prior to what we've fetched, so we skip.
            if idx_loc_ex_date == 0: 
                dbg_trace(f"Event date {ex_date.strftime('%Y-%m-%d')} for {ticker} is at or before start of price data. Skipping adjustment.")
                continue
            
            # Adjustments are applied to all data *before* the ex-dividend date.
            # `df_prices.index[:idx_loc_ex_date]` selects all rows from the beginning up to (but not including) the ex-dividend date.
            target_rows_index = df_prices.index[:idx_loc_ex_date]
            
            # Apply cash dividend adjustment
            if cash_div > 0:
                # The reference price for adjustment is the closing price on the day *before* the ex-dividend date.
                # `df_prices.index[idx_loc_ex_date - 1]` gives the index label for the day before ex-date.
                close_on_prev_day = df_prices.loc[df_prices.index[idx_loc_ex_date - 1], 'Close']
                adj_ratio_cash = None
                
                # Standard cash dividend adjustment: P_adj = P_orig * (Close_prev - CashDiv) / Close_prev
                if close_on_prev_day > 0 and close_on_prev_day > cash_div:
                    adj_ratio_cash = (close_on_prev_day - cash_div) / close_on_prev_day
                elif close_on_prev_day > 0 and close_on_prev_day <= cash_div : # Edge case: dividend is large relative to price
                    dbg_warning(f"Cash dividend ({cash_div}) for {ticker} on {ex_date.strftime('%Y-%m-%d')} "
                                f"is greater than or equal to Closing price on previous day ({close_on_prev_day}). Setting adj_ratio to very small value or handling as zero.")
                    # This case means the stock value effectively drops to (near) zero.
                    # Adjusting by (Close_prev_day - CashDividend) might result in zero or negative prices.
                    # A common way is to set adjusted prices to a very small positive number or handle as per broker's method.
                    # For simplicity, if (Close_prev_day - CashDividend) is <=0, we can make ratio very small.
                    # Or, more practically, if Close_prev_day - CashDividend <= 0, this implies the stock is almost worthless post-dividend.
                    # Let's make the adjusted prices reflect a tiny fraction of original.
                    adj_ratio_cash = 0.0001 # Arbitrary small factor to prevent zero/negative prices.
                                           # A more sophisticated handling might be needed depending on broker practices.
                else: # close_on_prev_day is 0 or negative (should not happen for valid price data)
                    dbg_warning(f"Invalid prev_day_close ({close_on_prev_day}) for cash dividend adjustment for {ticker} on {ex_date.strftime('%Y-%m-%d')}.")

                if adj_ratio_cash is not None:
                    # Apply the cash adjustment ratio to OHLC prices for all days before the ex-dividend date.
                    for col_name in ohlc_cols:
                        df_prices.loc[target_rows_index, col_name] *= adj_ratio_cash
            
            # Apply stock dividend adjustment
            if stock_div_r > 0:
                any_stock_dividend_applied = True # Mark that a stock dividend occurred.
                # Stock dividend adjustment: P_adj = P_orig / (1 + stock_div_r)
                # Example: 10% stock dividend (stock_div_r = 0.1), new price is old price / 1.1
                adj_ratio_stock = 1.0 / (1.0 + stock_div_r)

                # Temporarily convert Volume to float if it's int, to allow fractional results during adjustment,
                # before rounding back to int later.
                if 'Volume' in df_prices.columns and df_prices['Volume'].dtype == 'int':
                     df_prices['Volume'] = df_prices['Volume'].astype(float)

                # Apply the stock adjustment ratio to OHLC prices for all days before the ex-dividend date.
                for col_name in ohlc_cols:
                    df_prices.loc[target_rows_index, col_name] *= adj_ratio_stock
                
                # Adjust volume: V_adj = V_orig * (1 + stock_div_r)
                # This is equivalent to V_adj = V_orig / adj_ratio_stock
                if 'Volume' in df_prices.columns:
                    df_prices.loc[target_rows_index, 'Volume'] /= adj_ratio_stock # Or *= (1.0 + stock_div_r)

        # 6. Post-Adjustment Processing
        # If any stock dividend was applied, Volume might be float; round and convert back to int.
        if 'Volume' in df_prices.columns and any_stock_dividend_applied:
            df_prices['Volume'] = df_prices['Volume'].round().astype(int)

        # Round OHLC prices to a reasonable number of decimal places (e.g., 4).
        for col_name in ohlc_cols:
            if col_name in df_prices.columns:
                df_prices[col_name] = df_prices[col_name].round(4) 

        if 'Change' in df_prices.columns:
            # Recalculate the 'Change' column based on the adjusted 'Close' prices.
            # 'Change' is the difference between the current day's close and the previous day's close.
            prev_close = df_prices['Close'].shift(1) # Get previous day's close for each row.
            df_prices['Change'] = df_prices['Close'] - prev_close
            
            # The 'Change' for the first day in the series should be 0, as there's no prior day to compare.
            if not df_prices.empty and len(df_prices.index) > 0:
                 df_prices.loc[df_prices.index[0], 'Change'] = 0.0

        return df_prices


if __name__ == "__main__":
    fm = FindMind()
    
    # Example usage for fetch_dividend_result (can be used for debugging)
    # fm.fetch_dividend_result(symbol='2330', start_date='2020-01-01')

    # Example usage for fetch_adjusted_data:
    ticker_to_test = '2881' # Fuban

    print(f"Fetching adjusted data for {ticker_to_test} for the last 1 year...")
    df_adj_period = fm.fetch_adjusted_data(ticker=ticker_to_test, period=1)
    if not df_adj_period.empty:
        print(f"Adjusted data for {ticker_to_test} (last 1 year):")
        print(df_adj_period.head())
        print("...")
        print(df_adj_period.tail())
    else:
        print(f"No adjusted data returned for {ticker_to_test} with period=1.")

    # start_date_test = datetime(2023, 1, 1)
    ticker_to_test = '8069'
    start_date_test = datetime(1995, 1, 1)
    print(f"\nFetching adjusted data for {ticker_to_test} from {start_date_test.strftime('%Y-%m-%d')}...")
    df_adj_start_date = fm.fetch_adjusted_data(ticker=ticker_to_test, start_date=start_date_test)
    if not df_adj_start_date.empty:
        print(f"Adjusted data for {ticker_to_test} (from {start_date_test.strftime('%Y-%m-%d')}):")
        print(df_adj_start_date.head())
        print("...")
        print(df_adj_start_date.tail())
    else:
        print(f"No adjusted data returned for {ticker_to_test} with start_date {start_date_test.strftime('%Y-%m-%d')}.")

    # Test with a stock known for significant dividends/splits, e.g., '2603' (Evergreen Marine)
    ticker_evt_test = '2603'
    fetch_period_years = 10 # Ensure '2024-06-27' is covered from 2025-05-10
    print(f"\nFetching adjusted data for {ticker_evt_test} for the last {fetch_period_years} years...")
    df_adj_evt = fm.fetch_adjusted_data(ticker=ticker_evt_test, period=fetch_period_years)
    df_evt = fm.fetch_data(ticker=ticker_evt_test, period=fetch_period_years)
    if not df_adj_evt.empty:
        # print(df_adj_evt) # Print entire dataframe
        print(df_adj_evt.head())
        
        # Print data around '2024-06-27'
        target_date_str = '2024-06-27'
        start_slice_date = '2024-06-20'
        end_slice_date = '2024-07-05' # Give a bit of a window

        print(f"Original data for {ticker_evt_test} (last {fetch_period_years} years):")
        try:
            date_slice = df_evt.loc[start_slice_date:end_slice_date]
            if not date_slice.empty:
                print(date_slice)
            else:
                print(f"No data found in the range {start_slice_date} to {end_slice_date}.")
                # Fallback to printing head/tail if specific slice is empty but df is not
                print("\nShowing head and tail of the full dataset instead:")
                print(df_evt.head())
                print("...")
                print(df_evt.tail())

        except KeyError:
            print(f"Could not slice data for dates {start_slice_date} to {end_slice_date}. The dates might not exist in the index, or index is not sorted.")
            print("\nShowing head and tail of the full dataset instead:")
            print(df_evt.head())
            print("...")
            print(df_evt.tail())
        
        print(f"Adjusted data for {ticker_evt_test} (last {fetch_period_years} years):")
        print(f"\nData for {ticker_evt_test} around {target_date_str}:")
        try:
            date_slice = df_adj_evt.loc[start_slice_date:end_slice_date]
            if not date_slice.empty:
                print(date_slice)
            else:
                print(f"No data found in the range {start_slice_date} to {end_slice_date}.")
                # Fallback to printing head/tail if specific slice is empty but df is not
                print("\nShowing head and tail of the full dataset instead:")
                print(df_adj_evt.head())
                print("...")
                print(df_adj_evt.tail())

        except KeyError:
            print(f"Could not slice data for dates {start_slice_date} to {end_slice_date}. The dates might not exist in the index, or index is not sorted.")
            print("\nShowing head and tail of the full dataset instead:")
            print(df_adj_evt.head())
            print("...")
            print(df_adj_evt.tail())

        # You can compare df_adj_evt['Close'] with unadjusted close from a direct fetch_data call
        # or a financial website to verify adjustments.
    else:
        print(f"No adjusted data returned for {ticker_evt_test} with period={fetch_period_years}.")

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


