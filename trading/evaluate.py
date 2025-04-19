from datetime import timedelta
import traceback
from trading.analyzer import Analyzer
from strategy.strategy import *
from market.market import Market
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
        strategy_list=[DailyStrategy]

        market = Market()
        product_list = market.get_data_list()
        # product_list = ['1303', '1312']

        last_trading_day = datetime.now().date()

        while last_trading_day.weekday() >= 5:
            last_trading_day -= timedelta(days=1)

        dbg_info(f"Last Trad date {last_trading_day}")

        for each_strategy in strategy_list:
            each_strategy.trading_date = last_trading_day

            # for each_product in product_list:
            for each_idx in range(0, len(product_list)):
                each_product = product_list[each_idx]
                try:
                    dbg_info(f"[{each_idx:>2}/{len(product_list)}] {each_product}")
                    trade_analyzer = Analyzer(Market())
                    trade_analyzer.setup()
                    trade_analyzer.add_data([each_product])
                    trade_analyzer.add_strategy([each_strategy])
                    trade_analyzer.eval()
                    # Print detailed last trade information
                    trade_info = each_strategy.last_trade

                    if trade_info['action'] == 'buy':
                        dbg_info(f"Evaluation Trade {trade_info['code']}@{trade_info['date']}: Action: {trade_info['action']}, Current: {trade_info['current_price']:.2f}, Target: {trade_info['target_price']:.2f}, Stop: {trade_info['stop_price']:.2f}")
                        
                        candidate_dict[trade_info['code']] = {'strategy': each_strategy}
                    # else:
                    #     dbg_info(f"Last Trade {trade_info['code']}@{trade_info['date']}: Action: {trade_info['action']}, Current: {trade_info['current_price']:.2f}, Target: {trade_info['target_price']:.2f}, Stop: {trade_info['stop_price']:.2f}")
                except Exception as e:
                    dbg_warning(e)
                
                    traceback_output = traceback.format_exc()
                    dbg_warning(traceback_output)

        if len(candidate_dict) != 0:
            dbg_info(f"Candidate Checking:")
        for each_product in candidate_dict.keys():
            try:
                trade_analyzer = Analyzer(Market())
                trade_analyzer.setup()
                trade_analyzer.add_data([each_product])

                # Setting strategy
                target_strategy = candidate_dict[each_product]['strategy']
                # FIXME, it's kindle of a weird workaround. just need to fix it.
                target_strategy.reset_status(target_strategy)

                trade_analyzer.add_strategy([target_strategy])
                trade_analyzer.eval()

                # get report
                report = trade_analyzer.get_analysis()

                init_cash = report[0].get('init_cash', 0)
                final_cash = report[0].get('cash', 0)
                profit = (final_cash - init_cash) / init_cash * 100

                dbg_info(f"[{each_product}], {profit:.2f}%")
                if profit > candidate_profit_threshold:
                    buying_dict[each_product] = {'strategy': target_strategy, 'profit' : profit}
                # trade_analyzer.show_result()
            except Exception as e:
                dbg_warning(e)
            
                traceback_output = traceback.format_exc()
                dbg_warning(traceback_output)

        if len(buying_dict) != 0:
            dbg_info(f"Buying List:")
        for each_product in buying_dict.keys():
            dbg_info(f"Code: {each_product}, {buying_dict[each_product]['strategy']}, profit: {buying_dict[each_product]['profit']}")
        return buying_dict
    def selling_evaluation(self):
        pass

