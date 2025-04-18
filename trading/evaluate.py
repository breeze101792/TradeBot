
from trading.analyzer import Analyzer
from strategy.strategy import *
from market.market import Market
from strategy.daily import *

class Evaluate:
    def buying_evaluation(self):
        # TODO, Add broker trading here.
        ta = Analyzer(Market())

        # predefine for development
        strategyMgr = StrategyManager()
        strategy_list=[DailyStrategy]

        # product_list = ['2330', '2454']
        market = Market()
        product_list = market.get_data_list()[:50]
        # product_list = ['2330', '2454']

        for each_strategy in strategy_list:
            each_strategy.trading_date = datetime.now().date()
            for each_product in product_list:
                ta.setup()
                ta.add_data([each_product])
                ta.add_strategy([each_strategy])
                ta.eval()
        # ta.show_result()
    def selling_evaluation(self):
        pass

