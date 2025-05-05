from datetime import timedelta, date
import traceback
from dateutil.relativedelta import relativedelta

# from trading.analyzer import Analyzer
from backtest.backtest import Backtest as Analyzer
from strategy.strategy import *
from market.market import Market, MarketTime
from strategy.daily import *

class Evaluate:
    # threshold
    BUY_CANDIDATE_PROFIT_THRESHOLD = 1
    def __init__(self):
        # dev config
        self.flag_development = False
        # TODO, add multiple strategy support.
        self.default_strategy = DailyMACStrategy

        if self.flag_development:
            dbg_warning('Enable debug mode.')
            # Buy
            self.test_buy_list = ['2330', '1459', '1463', '1528', '2049', '2392', '2417', '2455', '2486', '3023', '3645', '4540', '4555', '5225', '6743', '8429']
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
                    dbg_info(f"[{each_idx + 1:>2}/{len(product_list)}] {each_product}")
                    # test only one year for accerate performance.
                    trade_analyzer.from_date=trade_analyzer.to_date - relativedelta(years=1)

                    trade_analyzer.setup()
                    trade_analyzer.add_data([each_product])
                    trade_analyzer.add_strategy([each_strategy])

                    # FIXME, it's kindle of a weird workaround. just need to fix it.
                    each_strategy.reset_status(each_strategy, clean_all = True)
                    each_strategy.trading_date = last_trading_day

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
        return candidate_dict
    def __buy_filering_profitable_product(self, candidate_dict):
        if len(candidate_dict) != 0:
            dbg_info(f"Candidate Checking:{candidate_dict.keys()}")
        buying_dict = dict()

        strategyMgr = StrategyManager()
        strategy_list=[self.default_strategy]
        market = Market()

        candidate_analyzer = Analyzer(market)
        candidate_analyzer.clean_result()
        for each_product in candidate_dict.keys():
            try:
                # test only one year for accerate performance.
                candidate_analyzer.from_date=candidate_analyzer.to_date - relativedelta(years=1)
                candidate_analyzer.setup()
                candidate_analyzer.add_data([each_product])

                # Setting strategy
                target_strategy = candidate_dict[each_product]['strategy']
                # FIXME, it's kindle of a weird workaround. just need to fix it.
                target_strategy.reset_status(target_strategy, clean_all = True)

                candidate_analyzer.add_strategy([target_strategy])
                candidate_analyzer.eval()

                # get report, get the latest one.
                report = candidate_analyzer.get_analysis()[-1]

                init_cash = report.get('init_cash', 0)
                final_cash = report.get('cash', 0)
                profit = (final_cash - init_cash) / init_cash * 100

                dbg_info(f"[{each_product}], {profit:.2f}%")
                if profit > self.BUY_CANDIDATE_PROFIT_THRESHOLD:
                    buying_dict[each_product] = {'strategy': target_strategy, 'profit' : profit}
            except Exception as e:
                dbg_warning(e)
            
                traceback_output = traceback.format_exc()
                dbg_warning(traceback_output)
        candidate_analyzer.show_result()

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
    def __sell_find_candidate(self, position_dict):
        # faking data, example input data.
        if self.flag_development and len(self.test_sell_list) > 0:
            position_dict = self.test_sell_list

        selling_list = []
        # selling_list = [{'symbol':'2330', 'size':5, 'initial_entry_price':1000, 'date':date.today(), 'strategy': DailyMACStrategy.NAME}] 

        if len(position_dict) == 0:
            dbg_debug(f"No position.")
            return []
        strategyMgr = StrategyManager()

        market = Market()
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

                # Add data for the specific stock
                selling_analyzer.add_data([symbol])

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
                target_strategy.reset_status(target_strategy, clean_all = True)
                # reset trading day to evaluate.
                target_strategy.trading_date = last_trading_day

                selling_analyzer.add_strategy([target_strategy])
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

