from datetime import timedelta
import traceback
from dateutil.relativedelta import relativedelta

# from trading.analyzer import Analyzer
from backtest.backtest import Backtest as Analyzer
from strategy.strategy import *
from market.market import Market, MarketTime
from strategy.daily import *

class Evaluate:
    def buying_evaluation(self):
        # threshold
        candidate_profit_threshold = 1

        candidate_dict = dict()
        buying_dict = dict()

        # TODO, Add broker trading here.

        # predefine for development
        strategyMgr = StrategyManager()
        strategy_list=[DailyMACStrategy]

        market = Market()
        product_list = market.get_data_list()
        # product_list = market.get_data_list()[:50]
        # product_list = ['2330', '1319', '1468', '1783', '2368', '2408', '2424', '2477', '3209', '3528', '5234', '6426', '6431']

        last_trading_day = MarketTime.get_previous_market_update_time().date()

        dbg_info(f"Last Trad date {last_trading_day}")

        trade_analyzer = Analyzer(market)
        trade_analyzer.clean_result()
        for each_strategy in strategy_list:
            each_strategy.trading_date = last_trading_day

            # for each_product in product_list:
            for each_idx in range(0, len(product_list)):
                each_product = product_list[each_idx]
                try:
                    dbg_info(f"[{each_idx + 1:>2}/{len(product_list)}] {each_product}")
                    # test only one year for accerate performance.
                    trade_analyzer.FROM_DATE=trade_analyzer.TO_DATE - relativedelta(years=1)

                    trade_analyzer.setup()
                    trade_analyzer.add_data([each_product])
                    trade_analyzer.add_strategy([each_strategy])
                    trade_analyzer.eval()
                    # Print detailed last trade information
                    trade_info = each_strategy.last_trade

                    if trade_info['action'] == 'buy':
                        dbg_info(f"Evaluation Trade {trade_info['code']}@{trade_info['date']}: Action: {trade_info['action']}, Current: {trade_info['current_price']:.2f}, Target: {trade_info['target_price']:.2f}, Stop: {trade_info['stop_price']:.2f}")
                        
                        candidate_dict[trade_info['code']] = {'strategy': each_strategy}
                except Exception as e:
                    dbg_warning(e)
                
                    traceback_output = traceback.format_exc()
                    dbg_warning(traceback_output)

        if len(candidate_dict) != 0:
            dbg_info(f"Candidate Checking:")

        candidate_analyzer = Analyzer(market)
        candidate_analyzer.clean_result()
        for each_product in candidate_dict.keys():
            try:
                # test only one year for accerate performance.
                candidate_analyzer.FROM_DATE=candidate_analyzer.TO_DATE - relativedelta(years=1)
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
                if profit > candidate_profit_threshold:
                    buying_dict[each_product] = {'strategy': target_strategy, 'profit' : profit}
            except Exception as e:
                dbg_warning(e)
            
                traceback_output = traceback.format_exc()
                dbg_warning(traceback_output)
        candidate_analyzer.show_result()

        if len(buying_dict) != 0:
            dbg_info(f"Buying List: {buying_dict.keys()}")
        for each_product in buying_dict.keys():
            product_info = market.get_data_info(each_product)
            dbg_info(f"Product: {each_product} {product_info['name']}/{product_info['category']}, {buying_dict[each_product]['strategy']}, profit: {buying_dict[each_product]['profit']:.2f}")
        return buying_dict
    def selling_evaluation(self, pos_list):
        # faking data, example input data.
        pos_list = [{'code':'2330', 'date':'2012-04-11', 'position':5, 'price':2000, 'strategy': DailyMACStrategy.NAME}] 

        selling_list = []
        # selling_list = [{'code':'2330', 'position':5, 'price':1000, 'strategy': DailyMACStrategy.NAME}] 
        

        if len(pos_list) == 0:
            dbg_info(f"No position.")
            return []
        strategyMgr = StrategyManager()

        market = Market()
        selling_analyzer = Analyzer(market)
        selling_analyzer.clean_result()

        last_trading_day = MarketTime.get_previous_market_update_time().date()
        dbg_info(f"Last Trad date {last_trading_day}")

        # for each_product in candidate_dict.keys():
        for each_product in pos_list:
            try:
                code = each_product['code']
                position_size = each_product['position'] # Size of the original buy order
                strategy_name = each_product['strategy']
                purchase_date = each_product['date']     # Date of the original buy
                purchase_price = each_product['price']   # Price of the original buy

                dbg_info(f"Evaluating selling condition for {code}, bought on {purchase_date} at {purchase_price}, size {position_size}, strategy {strategy_name}")

                # test only one year for accelerate performance.
                # TODO: Consider if FROM_DATE should be relative to purchase_date?
                selling_analyzer.FROM_DATE = selling_analyzer.TO_DATE - relativedelta(years=1)
                selling_analyzer.setup() # Setup Cerebro instance

                # Add data for the specific stock
                selling_analyzer.add_data([code])

                # --- Convert current position info to order_history format ---
                # Format: tuple of tuples -> ((datetime, size, price, data_name),)
                # Size is positive because it represents the historical buy order.
                order_history = ((purchase_date, position_size, purchase_price, code),)
                # ---

                # Add the historical buy order to the analyzer
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

                if trade_info['action'] == 'sell':
                    selling_list.append({'code':trade_info['code'], 'position':0, 'price':trade_info['current_price'], 'strategy': target_strategy})
            except Exception as e:
                dbg_warning(e)
            
                traceback_output = traceback.format_exc()
                dbg_warning(traceback_output)
        # selling_analyzer.show_result()

        if len(selling_list) != 0:
            dbg_info(f"Selling List: {selling_list}")
        for each_product in selling_list:
            product_info = market.get_data_info(each_product['code'])
            dbg_info(f"Product: {each_product['code']} {product_info['name']}/{product_info['category']}, {each_product['strategy']}, pos: {each_product['position']:.2f}, price: {each_product['price']:.2f}")

