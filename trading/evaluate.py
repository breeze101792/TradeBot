from datetime import timedelta, date, datetime
import traceback
from dateutil.relativedelta import relativedelta
import pandas as pd
from tabulate import tabulate

# from trading.analyzer import Analyzer
from backtest.backtest import Backtest as Analyzer
from strategy.strategy import StrategyManager
from market.market import Market, MarketTime
from broker.brokermanager import BrokerManager
from broker.order.constant import OrderPrice, OrderAction
from trading.traderecord import Recorder
from core.config import *

from strategy.candidate.mac import MovingAverageCrossoverStrategy
from strategy.candidate.bm import BreakoutMomentumStrategy
from strategy.candidate.rsi import RelativeStrengthIndexStrategy

class Evaluate:
    # threshold
    BUY_CANDIDATE_SCORE_THRESHOLD = 1
    BUY_CANDIDATE_SQN_THRESHOLD = 1.5
    def __init__(self):
        # TODO, add multiple strategy support.
        self.stra_mgr = StrategyManager()
        self.market = Market()

        # self.strategy_list = [MovingAverageCrossoverStrategy, RelativeStrengthIndexStrategy, BreakoutMomentumStrategy]
        self.strategy_list = self.stra_mgr.get_strategy_list([StrategyManager.Level.OFFICIAL])
        self.default_strategy = self.strategy_list[0]
        dbg_debug(f"default strategy: {self.default_strategy}, Strategy list: {self.strategy_list}")

        self.cm = AppConfigManager()

    def __buy_find_candidate(self, product_list = None):

        candidate_dict = dict()

        if product_list is None:
            product_list = self.market.get_data_list()
            dbg_info(f"Use all products form market.")

        last_trading_day = MarketTime.get_previous_market_update_time()

        dbg_debug(f"Find product on {last_trading_day} with {len(product_list)} products.")

        trade_broker = BrokerManager()
        trade_analyzer = Analyzer(self.market)
        trade_analyzer.clean_result()

        # for each_product in product_list:
        for each_idx in range(0, len(product_list)):
            each_product = product_list[each_idx]

            # NOTE. ignore holdings.
            each_position = trade_broker.get_position_by_symbol(each_product)
            if each_position is not None and each_position.size != 0:
                dbg_debug(f"[{each_product}] Skipping buy evaluation: already holding position (size: {each_position.size}).")
                continue

            for each_strategy in self.strategy_list:
                try:
                    dbg_info(f"[{each_idx + 1:>2}/{len(product_list)}] {each_product}" , prefix = '\r',end=' ' * 10)
                    # test only one year for accerate performance.
                    trade_analyzer.to_date=last_trading_day
                    trade_analyzer.from_date=trade_analyzer.to_date - relativedelta(years=1)

                    trade_analyzer.setup()
                    trade_analyzer.add_symbol([each_product])
                    trade_analyzer.add_strategy([each_strategy], last_trading_day = last_trading_day.date())

                    # FIXME, it's kindle of a weird workaround. just need to fix it.
                    # each_strategy.reset_status(each_strategy, clean_all = True)
                    # each_strategy.trading_date = last_trading_day

                    trade_analyzer.eval()
                    # Print detailed last trade information
                    # trade_info = each_strategy.last_trade
                    trade_info = trade_analyzer.get_last_trade()[0]

                    if trade_info['action'] == 'buy':
                        if trade_info['symbol'] not in candidate_dict:
                            dbg_info(f"Evaluation Trade {trade_info['symbol']}@{trade_info['date']}: Action: {trade_info['action']}, Current: {trade_info['price']:.2f}, size: {trade_info['size']:.2f}")
                            candidate_dict[trade_info['symbol']] = {'strategy': each_strategy}
                            # NOTE. if candidated, we ignore the following strategy test.
                            break
                        else:
                            dbg_info(f"Duplicated! Evaluation Trade {trade_info['symbol']}@{trade_info['date']}: Action: {trade_info['action']}, Current: {trade_info['price']:.2f}, size: {trade_info['size']:.2f}")
                    else:
                        dbg_trace(f"Evaluation Trade {trade_info['symbol']}@{trade_info['date']}: Action: {trade_info['action']}, Current: {trade_info['price']:.2f}, size: {trade_info['size']:.2f}")
                except Exception as e:
                    dbg_warning(e)
                
                    traceback_output = traceback.format_exc()
                    dbg_warning(traceback_output)
        dbg_debug(f"All product evaluated.", prefix='\n')
        return candidate_dict
    def __buy_filering_profitable_product(self, candidate_dict):
        if len(candidate_dict) == 0:
            return dict()
        dbg_info(f"Candidate Checking:{candidate_dict.keys()}")
        candidate_buying_dict = dict()
        buying_dict = dict()

        last_trading_day = MarketTime.get_previous_market_update_time()
        candidate_analyzer = Analyzer(self.market)
        candidate_analyzer.clean_result()
        candidate_keys = list(candidate_dict.keys())
        dbg_info(f"Start filtering.")
        for each_idx, each_product in enumerate(candidate_keys):
            try:
                dbg_info(f"[{each_idx + 1:>2}/{len(candidate_keys)}] [{each_product}] ", prefix='\r', end=' ' * 10)
                # test only one year for accerate performance.
                candidate_analyzer.to_date=last_trading_day
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

            except Exception as e:
                dbg_warning(e)
            
                traceback_output = traceback.format_exc()
                dbg_warning(traceback_output)
        # candidate_analyzer.show_result()

        # sorting with score and list it. add top 3 product to buying_dict.
        sorted_candidates = sorted(candidate_buying_dict.items(), key=lambda item: item[1].get('score', invalid_number), reverse=True)

        # Add positive products to buying_dict
        for product, data in sorted_candidates:
            ###############################
            ## Check evaluation
            ###############################
            # dbg_debug(f"  - Checking {product}: Score={data['score']:.2f} (>{Evaluate.BUY_CANDIDATE_SCORE_THRESHOLD}), SQN={data['sqn']:.2f} (>{Evaluate.BUY_CANDIDATE_SQN_THRESHOLD})")
            if data['score'] > Evaluate.BUY_CANDIDATE_SCORE_THRESHOLD and data['sqn'] > Evaluate.BUY_CANDIDATE_SQN_THRESHOLD:
                buying_dict[product] = data

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
    def buying_evaluation(self, product_list = None):
        candidate_dict = self.__buy_find_candidate(product_list = product_list)

        buying_dict = self.__buy_filering_profitable_product(candidate_dict)

        # dump buying data list.
        if len(buying_dict) != 0:
            dbg_debug(f"Buying List: {buying_dict.keys()}")
            # Prepare data for tabulation
            headers = ["Product", "Name", "Category", "Strategy", "Profit (%)", "Sharpe", "VWR", "Drawdown (%)", "SQN", "Score"]
            table_data = []
            for product, data in buying_dict.items():
                product_info = self.market.get_data_info(product)
                table_data.append([
                    product,
                    product_info.get('name', 'N/A'),
                    product_info.get('category', 'N/A'),
                    data['strategy'].NAME,
                    f"{data['profit']:.2f}",
                    f"{data['sharpe']:.2f}",
                    f"{data['vwr']:.2f}",
                    f"{data['drawdown']:.2f}",
                    f"{data['sqn']:.2f}",
                    f"{data['score']:.2f}"
                ])
            print("\n" + tabulate(table_data, headers=headers, tablefmt="grid"))
        else:
            dbg_debug(f"No buying candidates found.")

        return buying_dict
    def __get_realtime_data_list(self, symbol):
        # we append the last day to daily data for evaluation.
        trade_broker = BrokerManager()

        temp_df = self.market.get_data(symbol) # df with DatetimeIndex
        
        if temp_df is None or temp_df.empty:
            dbg_warning(f"No historical data found for {symbol}. Skipping sell evaluation for this symbol.")
            return None

        # dbg_debug(f"Original data for {symbol} (tail before modification):\n{temp_df.tail()}")

        # 'price' variable will store the latest price
        price = trade_broker.get_last_price(symbol, OrderPrice.BID) # float 
        if price is None or price <= 0:
            dbg_warning(f"Current price for {symbol} is {price}.")
            return None
        # current_trading_day is a datetime.date object, defined earlier in the method

        current_date = datetime.now().date()

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

        dbg_trace(f"{symbol} tail data to daily list, current price: {price}")
        
        # Fake other critical data if necessary.
        # For 'Change', if it represents (Close - Open), it would be 0.
        # If (Close - PrevClose), it would need PrevClose. For simplicity, set to 0.
        if 'Change' in current_day_data:
            current_day_data['Change'] = 0.0
        
        # Ensure Volume, Turnover, Transaction are not None if they were from an empty base
        for col_name in ['Volume', 'Turnover', 'Transaction']:
            if col_name in current_day_data and current_day_data[col_name] is None:
                current_day_data[col_name] = 0

        # Check if any entry for the current date already exists in the DataFrame's index.
        # This ignores the time component for the check.
        existing_rows = temp_df[temp_df.index.date == current_date]

        if not existing_rows.empty:
            # An entry for today already exists. Update the last one for this date.
            existing_ts_to_update = existing_rows.index[-1]
            dbg_warning(f"Updating data for {symbol} on {existing_ts_to_update} with Close price {price}")
            # Update existing row
            for col, value in current_day_data.items():
                if col in temp_df.columns: # Ensure column exists before assignment
                    temp_df.loc[existing_ts_to_update, col] = value
            target_df = temp_df
        else:
            # No entry for today, append a new one.
            # Use a timestamp at midnight for the new row's index.
            new_row_ts = pd.Timestamp(current_date)
            dbg_trace(f"Appending new data for {symbol} on {new_row_ts} with Close price {price}")
            # Create a new row as a DataFrame
            new_row_df = pd.DataFrame([current_day_data], index=[new_row_ts])
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
        selling_eval_result_list = []
        selling_list = []
        # selling_list = [{'symbol':'2330', 'size':5, 'initial_entry_price':1000, 'date':date.today(), 'strategy': MovingAverageCrossoverStrategy.NAME}] 

        if len(position_dict) == 0:
            dbg_debug(f"No position.")
            return []

        trade_broker = BrokerManager()
        recorder = Recorder()

        selling_analyzer = Analyzer(self.market)
        selling_analyzer.clean_result()

        last_trading_day = MarketTime.get_previous_market_update_time()
        dbg_debug(f"Evaluating {len(position_dict)} products with last Trad date {last_trading_day}")

        # Iterate through positions provided by the broker (dict: {symbol: Position_object})
        for symbol, position_obj in position_dict.items():
            try:
                # Init with position_obj as fallback
                position_size = position_obj.size
                purchase_date = position_obj.open_date
                purchase_price = position_obj.initial_entry_price
                strategy_name = self.default_strategy.NAME # Default strategy

                # --- Get position data from Recorder or Broker ---
                open_trade = next((t for t in recorder.get_records(symbol) if t.is_open), None)
                order_history = None

                # if open_trade and open_trade.symbol == symbol:
                if open_trade:
                    dbg_debug(f"Found open trade for {symbol} in recorder. Using recorded data.{open_trade}")
                    strategy_name = open_trade.strategy if open_trade.strategy else strategy_name

                    # Construct order_history from all buy transactions in the trade
                    buy_transactions = []
                    for trans in open_trade.transactions:
                        # Example: order_history = (('2012-04-11', 10, 100.50, 'AAPL'), ('2012-05-01', -10, 105.20, 'AAPL'))
                        if trans['action'] == OrderAction.BUY:
                            trans_date = datetime.fromtimestamp(trans['timestamp'] / 1000).date()
                            buy_transactions.append((trans_date, trans['size'], trans['price'], symbol))
                        elif trans['action'] == OrderAction.SELL:
                            trans_date = datetime.fromtimestamp(trans['timestamp'] / 1000).date()
                            buy_transactions.append((trans_date, -trans['size'], trans['price'], symbol))

                    if buy_transactions:
                        order_history = tuple(buy_transactions)

                else:
                    if open_trade is not None:
                        dbg_warning(f"No open trade for {symbol}/{open_trade.symbol} in recorder. Using data from broker.")
                    else:
                        dbg_warning(f"No open trade for {symbol} in recorder. Using data from broker.")
                
                if order_history is None:
                    # Fallback or default order history if not created from recorder
                    order_history = ((purchase_date, position_size, purchase_price, symbol),)

                dbg_debug(order_history)

                # --- Strategy Assumption ---
                # FIXME: The Position object doesn't store the entry strategy.
                # Currently assuming the default strategy for evaluating sell conditions for ALL positions.
                # A better approach would be to store the strategy with the position.
                # strategy_name is now set above based on recorder or default
                # ---

                # Ensure we have valid data to proceed
                if not purchase_date or purchase_price <= 0 or position_size <= 0:
                    dbg_warning(f"Skipping evaluation for {symbol}: Missing or invalid position data (Date: {purchase_date}, Price: {purchase_price}, Size: {position_size})")
                    continue

                dbg_debug(f"Evaluating for {symbol} using strategy {strategy_name}")

                selling_analyzer.setup() # Setup Cerebro instance

                # test only one year for accelerate performance.
                # TODO: Consider if from_date should be relative to purchase_date?
                selling_analyzer.to_date = last_trading_day
                selling_analyzer.from_date = selling_analyzer.to_date - relativedelta(years=1)

                # Add the combined/updated data feed to the analyzer
                target_df = self.__get_realtime_data_list(symbol)
                modified_last_trading_day = last_trading_day
                if target_df is not None:
                    modified_last_trading_day = target_df.index.max()
                    selling_analyzer.to_date = modified_last_trading_day
                    selling_analyzer.add_data_frame([{'symbol':symbol, 'data':target_df}])
                    # print(target_df)
                else:
                    dbg_warning(f'Can not get lastest price of {symbol}. Use previous date instead.')
                    selling_analyzer.add_symbol([symbol])
                # dbg_error(f"trading date: {modified_last_trading_day}, {target_df.index.max()}")

                # Add the historical buy order context to the analyzer
                selling_analyzer.add_history(order_history)

                # Setting strategy used for the original purchase
                target_strategy = self.stra_mgr.get_strategy_by_name(strategy_name)
                # FIXME, it's kindle of a weird workaround. just need to fix it.
                # target_strategy.reset_status(target_strategy, clean_all = True)
                # # reset trading day to evaluate.
                # target_strategy.trading_date = last_trading_day

                selling_analyzer.add_strategy([target_strategy], last_trading_day = modified_last_trading_day.date())
                selling_analyzer.eval()

                last_price = target_df['Close'].iloc[-1] if target_df is not None and not target_df.empty else None
                # Print detailed last trade information
                # trade_info = target_strategy.last_trade
                trade_info = selling_analyzer.get_last_trade()[0]
                selling_eval_result_list.append({
                    'symbol': symbol,
                    'open': purchase_date.isoformat(),
                    'action': trade_info.get('action', 'None'), # Sell the position size strategy decided.
                    'entry_price':purchase_price,
                    'last_price': last_price, 
                    'realtime_pl': (last_price/purchase_price - 1) * 100 if last_price is not None else None, 
                    'hoding_size': position_size, # current holding position size
                    'selling_price': trade_info.get('price', 0.0), # Target sell price from strategy (might be indicative)
                    'selling_size': trade_info.get('size', 0), # Sell the position size strategy decided.
                    'strategy': target_strategy # Keep strategy object if needed later
                })

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
                    dbg_debug(f"No sell signal for {symbol} on {modified_last_trading_day.date()}. Last action: {trade_info}")
                else:
                    # Assuming dbg_debug exists
                    dbg_debug(f"No trade info generated for {symbol} by strategy {strategy_name} on {modified_last_trading_day.date()}.")

            except Exception as e:
                dbg_warning(f"Error evaluating sell condition for {symbol}: {e}")
            
                traceback_output = traceback.format_exc()
                dbg_warning(traceback_output)
        
        # Prepare data for tabulation of selling evaluation results
        if len(selling_eval_result_list) != 0:
            headers = ["Symbol", "Open Date", "Action", "Holding Size", "Entry Price", "Current Price", "Realtime P/L (%)", "Selling Price", "Selling Size", "Strategy"]
            table_data = []
            for result in selling_eval_result_list:
                table_data.append([
                    result.get('symbol', 'N/A'),
                    result.get('open', 'N/A'),
                    result.get('action', 'N/A'),
                    f"{result.get('hoding_size', 0)}",
                    f"{result.get('entry_price', 0.0):.2f}",
                    f"{result.get('last_price', 0.0):.2f}", # Use 'last_price' which is the current price
                    f"{result.get('realtime_pl', 0.0):.2f}",
                    f"{result.get('selling_price', 0.0):.2f}",
                    f"{result.get('selling_size', 0)}",
                    result.get('strategy').NAME if result.get('strategy') else 'N/A'
                ])
            print("\n--- Selling Evaluation Results ---")
            print("\n" + tabulate(table_data, headers=headers, tablefmt="grid"))
            print("----------------------------------")
        else:
            dbg_info("No selling evaluation results to display.")

        # selling_analyzer.show_result()
        return selling_list
    def selling_evaluation(self, position_dict):
        selling_list = self.__sell_find_candidate(position_dict)

        if len(selling_list) != 0:
            dbg_debug(f"Potential Selling List: {selling_list}") # Renamed for clarity
        else:
            dbg_debug(f"No Potential Selling.")

        for sell_candidate in selling_list:
            # Use 'symbol' key which is consistent now
            symbol = sell_candidate['symbol']
            product_info = self.market.get_data_info(symbol)
            strategy_name = sell_candidate['strategy'].NAME # Get name from strategy object
            dbg_info(f"Product to Sell: {symbol} ({product_info.get('name', 'N/A')}/{product_info.get('category', 'N/A')}), Strategy: {strategy_name}, Size: {sell_candidate['size']}, Indicative Price: {sell_candidate['price']:.2f}")

        return selling_list # Return the list of dictionaries

