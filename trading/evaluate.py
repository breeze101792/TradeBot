from datetime import timedelta
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
        if self.flag_development:
            dbg_warning('Enable debug mode.')
            # Buy
            self.test_buy_list = ['1414', '2402', '3008', '3029', '6768', '6914', '8215']
            # Sell
            self.test_sell_list = [{'code':'2330', 'date':'2012-04-11', 'position':5, 'price':2000, 'strategy': DailyMACStrategy.NAME}] 
            self.test_sell_list.append({'code':'2454', 'date':'2012-04-11', 'position':5, 'price':1500, 'strategy': DailyMACStrategy.NAME})
    def __buy_find_candidate(self):

        candidate_dict = dict()

        # predefine for development
        strategyMgr = StrategyManager()
        strategy_list=[DailyMACStrategy]

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
                    trade_analyzer.FROM_DATE=trade_analyzer.TO_DATE - relativedelta(years=1)

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
                        dbg_info(f"Evaluation Trade {trade_info['code']}@{trade_info['date']}: Action: {trade_info['action']}, Current: {trade_info['price']:.2f}, size: {trade_info['size']:.2f}")
                        candidate_dict[trade_info['code']] = {'strategy': each_strategy}
                    # else:
                    #     dbg_info(f"Evaluation Trade {trade_info['code']}@{trade_info['date']}: Action: {trade_info['action']}, Current: {trade_info['price']:.2f}, size: {trade_info['size']:.2f}")
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
        strategy_list=[DailyMACStrategy]
        market = Market()

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
        if self.flag_development:
            position_dict = self.test_sell_list

        selling_list = []
        # selling_list = [{'code':'2330', 'position':5, 'price':1000, 'strategy': DailyMACStrategy.NAME}] 

        if len(position_dict) == 0:
            dbg_info(f"No position.")
            return []
        strategyMgr = StrategyManager()

        market = Market()
        selling_analyzer = Analyzer(market)
        selling_analyzer.clean_result()

        last_trading_day = MarketTime.get_previous_market_update_time().date()
        dbg_info(f"Last Trad date {last_trading_day}")

        # for each_product in candidate_dict.keys():
        for each_product in position_dict:
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
                    selling_list.append({'code':trade_info['code'], 'size':trade_info['size'], 'price':trade_info['price'], 'strategy': target_strategy})
            except Exception as e:
                dbg_warning(e)
            
                traceback_output = traceback.format_exc()
                dbg_warning(traceback_output)
        # selling_analyzer.show_result()
        return selling_list
    def selling_evaluation(self, position_dict):
        market = Market()
        selling_list = self.__sell_find_candidate(position_dict)

        if len(selling_list) != 0:
            dbg_info(f"Selling List: {selling_list}")
        for each_product in selling_list:
            product_info = market.get_data_info(each_product['code'])
            dbg_info(f"Product: {each_product['code']} {product_info['name']}/{product_info['category']}, {each_product['strategy']}, size: {each_product['size']:.2f}, price: {each_product['price']:.2f}")

