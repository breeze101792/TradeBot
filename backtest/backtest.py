# system file
import traceback
import time

import backtrader as bt
import pandas as pd
from datetime import datetime

# Local file
from utility.debug import *
from core.database import *
from market.market import *
from market.provider.yahoo import *
from market.provider.twse import *
from backtest.backtest import *
from strategy.strategy import *

class Backtest:
    def __init__(self):
        self.market = Market()
        self.default_strategy = MovingAverageCrossover
        self.default_product_list = self.market.get_top_product_list()

    def __backtrading(self, cerebro):
        init_cash = 1000000 

        # Setup init cash
        cerebro.broker.set_cash(init_cash)
        # Set commission
        cerebro.broker.setcommission(commission=0.001)
        # set perc
        cerebro.broker.set_slippage_perc(perc=0.001)
        # Add analyzer
        cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name="annual_return")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.02)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
        cerebro.addanalyzer(bt.analyzers.VWR, _name="vwr")


        # cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="TradeAnalyzer")
        # Do backtesting
        results = cerebro.run()
        strat = results[0]  # Get strategy result.

        dbg_info(f"Init cash({init_cash}), Profit: {(cerebro.broker.getvalue() - init_cash):.2f}/({(cerebro.broker.getvalue() - init_cash)/init_cash*100:.2f}%)")
        # Annual return
        dbg_info("Annual return:")
        for year, ret in strat.analyzers.annual_return.get_analysis().items():
            dbg_info(f"  {year}: {ret:.2%}")

        # Sharpe Ratio
        sharpe_ratio = strat.analyzers.sharpe.get_analysis().get("sharperatio", None)
        dbg_info(f"Sharpe Ratio: {sharpe_ratio:.2f}" if sharpe_ratio else "📈 sharpe_ratio: Can't calculate")

        vwr = strat.analyzers.vwr.get_analysis().get("vwr", None)
        dbg_info(f"VW Ratio: {vwr:.2f}" if vwr else "📈 VWR: sharpe_ratio: Can't calculate")

        # Drawdown
        drawdown = strat.analyzers.drawdown.get_analysis()
        dbg_info(f"Drawdown: {drawdown['max']['drawdown']:.2f}%")

        # Drawdown
        # tradeanalyzer = strat.analyzers.TradeAnalyzer.get_analysis()
        # dbg_info(f"TradeAnalyzer: {tradeanalyzer}")

        # SQN
        sqn = strat.analyzers.sqn.get_analysis()
        dbg_info(f"SQN: {sqn['sqn']:.2f}, Trad: {sqn['trades']}")

        # Do ploting
        # cerebro.plot()
        ###############################################################

        # dbg_info("Tracking List: " + product_list.__str__())
        return results

    def testSingle(self, productid = None, strategy = None, from_date=datetime(2020, 1, 1), to_date=datetime(2025, 1, 1)):
        # Default testing.
        if strategy is None:
            strategy = self.default_strategy

        if productid is None:
            productid = self.default_product_list[0]
        # TODO Impl Test
        ###############################################################
        # Init Backtrader
        cerebro = bt.Cerebro()

        df = self.market.get_data(productid)
        data = bt.feeds.PandasData(dataname=df, fromdate=from_date, todate=to_date)

        # Add data to enginee
        cerebro.adddata(data, name=productid)


        dbg_info("Start running Strategy.")

        # Load strategy
        cerebro.addstrategy(strategy)

        self.__backtrading(cerebro)
    def testBatch(self, product_list = None, strategy_list = None, from_date=datetime(2020, 1, 1), to_date=datetime(2025, 1, 1)):
        dbg_info('Tset Start.')

        # Default testing.
        if strategy_list is None:
            strategy_list = [self.default_strategy]

        if product_list is None:
            product_list = self.default_product_list

        for each_strategy in strategy_list:
            dbg_trace('Test run with '.format(each_strategy))
            try:
                # TODO Impl Test
                ###############################################################
                # Init Backtrader
                cerebro = bt.Cerebro()

                for each_product in product_list:
                    dbg_info("Product List: ", each_product.__str__())
                    try:
                        df = self.market.get_data(each_product)
                        data = bt.feeds.PandasData(dataname=df, fromdate=from_date, todate=to_date)

                        # Add data to enginee
                        cerebro.adddata(data, name=each_product)
                    except Exception as e:
                        dbg_error("Disable ticker: ", each_product)
                        self.update_tracking_list(each_product, False)
                        dbg_error(e)

                        traceback_output = traceback.format_exc()
                        dbg_error(traceback_output)
                        continue


                dbg_info("Start running Strategy.")
                # Load strategy
                cerebro.addstrategy(each_strategy)

                self.__backtrading(cerebro)

                # Do ploting
                # cerebro.plot()
                ###############################################################


                # dbg_info("Tracking List: " + product_list.__str__())

            except KeyboardInterrupt:
                dbg_warning("Keyboard Interupt.")
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)

