from datetime import timedelta, date
import traceback
from dateutil.relativedelta import relativedelta
import pandas as pd
from tabulate import tabulate

# from trading.analyzer import Analyzer
from backtest.backtest import Backtest as Analyzer
from strategy.strategy import StrategyManager
from market.market import Market, MarketTime
from broker.brokermanager import BrokerManager
from core.config import *

class Evaluate:
    # threshold
    BUY_CANDIDATE_PROFIT_THRESHOLD = 1
    def __init__(self, development = False):
        # TODO, add multiple strategy support.
        stra_mgr = StrategyManager()
        self.default_strategy = stra_mgr.get_default_strategy()
        dbg_info(f"default strategy: {self.default_strategy}")

        self.cm = AppConfigManager()

        # debug mode
        self.flag_development = development
        if self.flag_development and self.cm.get('debug.development') is True:
            dbg_warning('Enable debug mode.')
            # Buy
            self.test_buy_list = ['0050', '2330', '2454', '2028', '8404']
            # Sell
            self.test_sell_list = []
            # self.test_sell_list.append({'symbol':'2330', 'open_date':date.today().isoformat(), 'size':5, 'initial_entry_price':2000, 'strategy': self.default_strategy.NAME})
            # self.test_sell_list.append({'symbol':'2454', 'open_date':date.today().isoformat(), 'size':5, 'initial_entry_price':1500, 'strategy': self.default_strategy.NAME})

    def __buy_find_candidate(self):

        candidate_dict = dict()

        # predefine for development
        strategyMgr = StrategyManager()
        strategy_list=[self.default_strategy]

        market = Market()
        product_list = market.get_data_list()
        if self.flag_development:
            # product_list = market.get_data_list()[:50]
            product_list = self.test_buy_list

        last_trading_day = MarketTime.get_previous_market_update_time().date()

        dbg_info(f"Last Trad date {last_trading_day}")

        trade_analyzer = Analyzer(market)
        trade_analyzer.clean_result()
        for each_strategy in strategy_list:

            # for each_product in product_list:
            for each_idx in range(0, len(product_list)):
                each_product = product_list[each_idx]
                try:
                    dbg_info(f"[{each_idx + 1:>2}/{len(product_list)}] {each_product}" , prefix = '\r',end=' ' * 10)
                    # test only one year for accerate performance.
                    trade_analyzer.from_date=trade_analyzer.to_date - relativedelta(years=1)

                    trade_analyzer.setup()
                    trade_analyzer.add_symbol([each_product])
                    trade_analyzer.add_strategy([each_strategy], last_trading_day = last_trading_day)

                    # FIXME, it's kindle of a weird workaround. just need to fix it.
                    # each_strategy.reset_status(each_strategy, clean_all = True)
                    # each_strategy.trading_date = last_trading_day

                    trade_analyzer.eval()
                    # Print detailed last trade information
                    trade_info = each_strategy.last_trade

                    if trade_info['action'] == 'buy':
                        dbg_info(f"Evaluation Trade {trade_info['symbol']}@{trade_info['date']}: Action: {trade_info['action']}, Current: {trade_info['price']:.2f}, size: {trade_info['size']:.2f}")
                        candidate_dict[trade_info['symbol']] = {'strategy': each_strategy}
                    # else:
                    #     dbg_info(f"Evaluation Trade {trade_info['symbol']}@{trade_info['date']}: Action: {trade_info['action']}, Current: {trade_info['price']:.2f}, size: {trade_info['size']:.2f}")
                except Exception as e:
                    dbg_warning(e)
                
                    traceback_output = traceback.format_exc()
                    dbg_warning(traceback_output)
        dbg_info(f"All product evaluated.", prefix='\n')
        return candidate_dict
    def __buy_filering_profitable_product(self, candidate_dict):
        if len(candidate_dict) != 0:
            dbg_info(f"Candidate Checking:{candidate_dict.keys()}")
        candidate_buying_dict = dict()

        strategyMgr = StrategyManager()
        strategy_list=[self.default_strategy]
        market = Market()

        candidate_analyzer = Analyzer(market)
        candidate_analyzer.clean_result()
        candidate_keys = list(candidate_dict.keys())
        dbg_info(f"Start filtering.")
        for each_idx, each_product in enumerate(candidate_keys):
            try:
                dbg_info(f"[{each_idx + 1:>2}/{len(candidate_keys)}] [{each_product}] ", prefix='\r', end=' ' * 10)
                # test only one year for accerate performance.
                candidate_analyzer.from_date=candidate_analyzer.to_date - relativedelta(years=1)
                candidate_analyzer.setup()
                candidate_analyzer.add_symbol([each_product])

                # Setting strategy
                target_strategy = candidate_dict[each_product]['strategy']
                # FIXME, it's kindle of a weird workaround. just need to fix it.
                # target_strategy.reset_status(target_strategy, clean_all = True)

                candidate_analyzer.add_strategy([target_strategy])
                candidate_analyzer.eval()

                # get report, get the latest one.
                report = candidate_analyzer.get_analysis()[-1]

                invalid_number = float('nan')
                profit = report.get('profit', invalid_number)
                if profit is None or not isinstance(profit, (int, float)): profit = invalid_number

                sharpe = report.get('sharpe', invalid_number)
                if sharpe is None or not isinstance(sharpe, (int, float)): sharpe = invalid_number

                vwr = report.get('vwr', invalid_number)
                if vwr is None or not isinstance(vwr, (int, float)): vwr = invalid_number

                drawdown = report.get('drawdown', {}).get('max', {}).get('drawdown', invalid_number)
                if drawdown is None or not isinstance(drawdown, (int, float)): drawdown = invalid_number

                sqn = report.get('sqn', {}).get('sqn', invalid_number)
                if sqn is None or not isinstance(sqn, (int, float)): sqn = invalid_number

                # evaluation
                score = report.get('score', invalid_number)

                candidate_buying_dict[each_product] = {
                    'strategy': target_strategy,
                    'profit' : profit,
                    'sharpe': sharpe,
                    'vwr': vwr,
                    'drawdown': drawdown,
                    'sqn': sqn,
                    'score': score
                }

                # TODO, find a way to check in the early day.
                # if profit > self.BUY_CANDIDATE_PROFIT_THRESHOLD:
                #     candidate_buying_dict[each_product] = {'strategy': target_strategy, 'profit' : profit}

            except Exception as e:
                dbg_warning(e)
            
                traceback_output = traceback.format_exc()
                dbg_warning(traceback_output)
        # candidate_analyzer.show_result()

        buying_dict = {}
        # sorting with score and list it. add top 3 product to buying_dict.
        sorted_candidates = sorted(candidate_buying_dict.items(), key=lambda item: item[1].get('score', invalid_number), reverse=True)

        # Add top 3 products to buying_dict
        for i, (product, data) in enumerate(sorted_candidates):
            if i < 3: # Take top 3
                buying_dict[product] = data
            else:
                break

        # Prepare data for tabulation
        headers = ["Product", "Strategy", "Profit (%)", "Sharpe", "VWR", "Drawdown (%)", "SQN", "Score"]
        table_data = []
        for product, data in sorted_candidates:
            table_data.append([
                product,
                data['strategy'].NAME,
                f"{data['profit']:.2f}",
                f"{data['sharpe']:.2f}",
                f"{data['vwr']:.2f}",
                f"{data['drawdown']:.2f}",
                f"{data['sqn']:.2f}",
                f"{data['score']:.2f}"
            ])
        
        if len(table_data) != 0:
            dbg_info("\n" + tabulate(table_data, headers=headers, tablefmt="grid"))
        dbg_info(f"All {len(candidate_keys)} products are analysed. ", prefix='\n')

        return buying_dict
    def buying_evaluation(self):
        market = Market()

        candidate_dict = self.__buy_find_candidate()

        buying_dict = self.__buy_filering_profitable_product(candidate_dict)

        # dump buying data list.
        if len(buying_dict) != 0:
            dbg_info(f"Buying List: {buying_dict.keys()}")
        for each_product in buying_dict.keys():
            product_info = market.get_data_info(each_product)
            dbg_info(f"Product: {each_product} {product_info['name']}/{product_info['category']}, {buying_dict[each_product]['strategy']}, profit: {buying_dict[each_product]['profit']:.2f}")

        return buying_dict
    def __get_realtime_data_list(self, symbol):
        # we append the last day to daily data for evaluation.
        market = Market()
        trade_broker = BrokerManager()

        temp_df = market.get_data(symbol) # df with DatetimeIndex
        
        if temp_df is None or temp_df.empty:
            dbg_warning(f"No historical data found for {symbol}. Skipping sell evaluation for this symbol.")
            return None

        # dbg_debug(f"Original data for {symbol} (tail before modification):\n{temp_df.tail()}")

        # 'price' variable will store the latest price
        price = trade_broker.get_last_price(symbol) # float 
        if price == 0:
            dbg_warning(f"Current price for {symbol} is 0.")
            return None
        # current_trading_day is a datetime.date object, defined earlier in the method

        # Convert current_trading_day to pandas Timestamp for DataFrame indexing
        current_trading_day = datetime.now()
        last_trading_day_ts = pd.Timestamp(current_trading_day)

        # Prepare data for the current_trading_day
        # Initialize with previous day's data if available, else with defaults based on temp_df columns
        if not temp_df.empty:
            current_day_data = temp_df.iloc[-1].to_dict()
        else:
            # Should not happen if initial check temp_df.empty is robust
            # but as a fallback, create a structure based on columns
            current_day_data = {col: 0 for col in temp_df.columns if pd.api.types.is_numeric_dtype(temp_df[col])}
            for col in temp_df.columns:
                if col not in current_day_data: # For non-numeric or other types
                    current_day_data[col] = None 

        # Update OHLC with the latest price
        current_day_data['Open'] = price
        current_day_data['High'] = price
        current_day_data['Low'] = price
        current_day_data['Close'] = price

        dbg_info(f"{symbol} tail data to daily list, current price: {price}")
        
        # Fake other critical data if necessary.
        # For 'Change', if it represents (Close - Open), it would be 0.
        # If (Close - PrevClose), it would need PrevClose. For simplicity, set to 0.
        if 'Change' in current_day_data:
            current_day_data['Change'] = 0.0
        
        # Ensure Volume, Turnover, Transaction are not None if they were from an empty base
        for col_name in ['Volume', 'Turnover', 'Transaction']:
            if col_name in current_day_data and current_day_data[col_name] is None:
                current_day_data[col_name] = 0

        if last_trading_day_ts in temp_df.index:
            dbg_warning(f"Updating data for {symbol} on {last_trading_day_ts} with Close price {price}")
            # Update existing row
            for col, value in current_day_data.items():
                if col in temp_df.columns: # Ensure column exists before assignment
                    temp_df.loc[last_trading_day_ts, col] = value
            target_df = temp_df
        else:
            dbg_trace(f"Appending new data for {symbol} on {last_trading_day_ts} with Close price {price}")
            # Create a new row as a DataFrame
            new_row_df = pd.DataFrame([current_day_data], index=[last_trading_day_ts])
            # Ensure the new row DataFrame has the same index name as the original DataFrame
            new_row_df.index.name = temp_df.index.name if temp_df.index.name else 'Date'
            
            # Align columns with temp_df, new_row_df might have different columns or order
            # Reindex will add missing columns as NaN and drop extra columns.
            new_row_df = new_row_df.reindex(columns=temp_df.columns)

            # Fill any NaNs that might have been introduced by reindex if a column from temp_df
            # was not in current_day_data and not handled by initialization.
            # Example: fill numeric NaNs with 0.
            for col in new_row_df.columns:
                if new_row_df[col].isnull().any():
                    if pd.api.types.is_numeric_dtype(new_row_df[col]):
                        new_row_df[col].fillna(0, inplace=True)
                    # else: fill with empty string or other appropriate default for non-numeric

            target_df = pd.concat([temp_df, new_row_df])
            target_df.sort_index(inplace=True)
        
        dbg_debug(f"Target data for {symbol} (tail after modification):\n{target_df.tail()}")

        return target_df
    def __sell_find_candidate(self, position_dict):
        # faking data, example input data.
        if self.flag_development and len(self.test_sell_list) > 0:
            position_dict = self.test_sell_list

        selling_list = []
        # selling_list = [{'symbol':'2330', 'size':5, 'initial_entry_price':1000, 'date':date.today(), 'strategy': MovingAverageCrossoverStrategy.NAME}] 

        if len(position_dict) == 0:
            dbg_debug(f"No position.")
            return []
        strategyMgr = StrategyManager()

        market = Market()
        trade_broker = BrokerManager()

        selling_analyzer = Analyzer(market)
        selling_analyzer.clean_result()

        last_trading_day = MarketTime.get_previous_market_update_time().date()
        dbg_debug(f"Last Trad date {last_trading_day}")

        # Iterate through positions provided by the broker (dict: {symbol: Position_object})
        for symbol, position_obj in position_dict.items():
            try:
                # Extract details from the Position object
                position_size = position_obj.size # Current size of the position
                purchase_date = position_obj.open_date     # Date the position was opened (datetime.date object)
                purchase_price = position_obj.initial_entry_price   # Price of the first buy transaction

                # --- Strategy Assumption ---
                # FIXME: The Position object doesn't store the entry strategy.
                # Currently assuming the default strategy for evaluating sell conditions for ALL positions.
                # A better approach would be to store the strategy with the position.
                strategy_name = self.default_strategy.NAME
                # ---

                # Ensure we have valid data to proceed
                if not purchase_date or purchase_price <= 0 or position_size <= 0:
                    dbg_warning(f"Skipping evaluation for {symbol}: Missing or invalid position data (Date: {purchase_date}, Price: {purchase_price}, Size: {position_size})")
                    continue

                dbg_info(f"Evaluating for {symbol}, opened on {purchase_date.isoformat()} at initial price {purchase_price:.2f}, current size {position_size}, using strategy {strategy_name}")

                # test only one year for accelerate performance.
                # TODO: Consider if from_date should be relative to purchase_date?
                selling_analyzer.from_date = selling_analyzer.to_date - relativedelta(years=1)
                selling_analyzer.setup() # Setup Cerebro instance

                # Add the combined/updated data feed to the analyzer
                target_df = self.__get_realtime_data_list(symbol)
                if target_df is not None:
                    last_trading_day = datetime.now().date()
                    selling_analyzer.add_data_frame([{'symbol':symbol, 'data':target_df}])
                else:
                    selling_analyzer.add_symbol([symbol])

                # --- Convert current position info to order_history format ---
                # Format: tuple of tuples -> ((datetime, size, price, data_name),)
                # We use the initial purchase details to represent the historical buy order.
                # Note: Cerebro's add_history might expect datetime, but let's try with date first.
                # Size should be the original size, but using current size might be okay if strategy logic handles it.
                # Using initial_entry_price as the historical price.
                order_history = ((purchase_date, position_size, purchase_price, symbol),) # Using current size here
                # ---

                # Add the historical buy order context to the analyzer
                selling_analyzer.add_history(order_history)

                # Setting strategy used for the original purchase
                target_strategy = strategyMgr.get_strategy_by_name(strategy_name)
                # FIXME, it's kindle of a weird workaround. just need to fix it.
                # target_strategy.reset_status(target_strategy, clean_all = True)
                # # reset trading day to evaluate.
                # target_strategy.trading_date = last_trading_day

                selling_analyzer.add_strategy([target_strategy], last_trading_day = last_trading_day)
                selling_analyzer.eval()

                # Print detailed last trade information
                trade_info = target_strategy.last_trade

                # Check if the strategy generated a sell signal for the last trading day
                if trade_info and trade_info.get('action') == 'sell' and trade_info.get('symbol') == symbol:
                     # Ensure the sell signal corresponds to the evaluated symbol
                    dbg_trace(f"Sell signal generated for {symbol} by strategy {strategy_name}. Details: {trade_info}")
                    # Add details needed for the actual sell order
                    selling_list.append({
                        'symbol': trade_info['symbol'],
                        'size': trade_info['size'], # Sell the position size strategy decided.
                        'price': trade_info['price'], # Target sell price from strategy (might be indicative)
                        'strategy': target_strategy # Keep strategy object if needed later
                    })
                elif trade_info:
                    # Assuming dbg_debug exists in your system, similar to dbg_info/dbg_warning
                    dbg_debug(f"No sell signal for {symbol} on {last_trading_day}. Last action: {trade_info}")
                else:
                    # Assuming dbg_debug exists
                    dbg_debug(f"No trade info generated for {symbol} by strategy {strategy_name} on {last_trading_day}.")

            except Exception as e:
                dbg_warning(f"Error evaluating sell condition for {symbol}: {e}")
            
                traceback_output = traceback.format_exc()
                dbg_warning(traceback_output)
        # selling_analyzer.show_result()
        return selling_list
    def selling_evaluation(self, position_dict):
        market = Market()
        selling_list = self.__sell_find_candidate(position_dict)

        if len(selling_list) != 0:
            dbg_debug(f"Potential Selling List: {selling_list}") # Renamed for clarity
        else:
            dbg_debug(f"No Potential Selling.")

        for sell_candidate in selling_list:
            # Use 'symbol' key which is consistent now
            symbol = sell_candidate['symbol']
            product_info = market.get_data_info(symbol)
            strategy_name = sell_candidate['strategy'].NAME # Get name from strategy object
            dbg_info(f"Product to Sell: {symbol} ({product_info.get('name', 'N/A')}/{product_info.get('category', 'N/A')}), Strategy: {strategy_name}, Size: {sell_candidate['size']:.2f}, Indicative Price: {sell_candidate['price']:.2f}")

        return selling_list # Return the list of dictionaries

