# system file
import traceback
import time

import backtrader as bt
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Local file
from utility.debug import *
from utility.utils import *
from core.database import *
from market.market import *
from market.provider.yahoo import *
from market.provider.twse import *
from backtest.backtest import *
from strategy.strategy import *

class Backtest:
    INIT_CASH = 1000000
    COMMISSION = 0.001
    SLIPPAGE_PREC = 0.001
    TO_DATE=datetime.today()
    FROM_DATE=TO_DATE - relativedelta(years=5)

    def __init__(self, market):
        self.market = market
        self.default_strategy = MovingAverageCrossover
        self.default_product_list = self.market.get_top_product_list()

        self.cerebro = None
        self.data_list = []
        self.strategy_list = []
        self.result_list = []

    def __setup_broker(self, cerebro = None):
        if cerebro is None:
            cerebro = self.cerebro

        # Setup init cash
        cerebro.broker.set_cash(self.INIT_CASH)
        # Set commission
        cerebro.broker.setcommission(commission=self.COMMISSION)
        # set perc
        cerebro.broker.set_slippage_perc(perc=self.SLIPPAGE_PREC)
    def __setup_analyzer(self, cerebro = None):
        if cerebro is None:
            cerebro = self.cerebro
        # Add analyzer
        dbg_trace('Add analyzer.')
        cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name="annual_return")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.02)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
        cerebro.addanalyzer(bt.analyzers.VWR, _name="vwr")
        # cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="TradeAnalyzer")
    def __analyze(self, strategy_list, cerebro = None):
        invalid_number = 101
        if cerebro is None:
            cerebro = self.cerebro
        # result_list = []

        for each_strategy in strategy_list:
            result_item = {}
            result_item['data'] = self.data_list
            result_item['strategy'] = [each_stra.NAME for each_stra in self.strategy_list]
            result_item['init_cash'] = self.INIT_CASH
            result_item['cash'] = cerebro.broker.getvalue()

            # ann_returN
            result_item['annual_return'] = {}
            for year, ret in each_strategy.analyzers.annual_return.get_analysis().items():
                # print(f"{year}: {ret:.2%}, ")
                # ann_message += f"{year}: {ret:.2%}, "
                result_item['annual_return'][year] = ret * 100

            result_item['sharpe'] = each_strategy.analyzers.sharpe.get_analysis().get("sharperatio", invalid_number)
            result_item['vwr'] = each_strategy.analyzers.vwr.get_analysis().get("vwr", invalid_number)

            result_item['drawdown'] = each_strategy.analyzers.drawdown.get_analysis()
            result_item['sqn'] = each_strategy.analyzers.sqn.get_analysis()

            self.result_list.append(result_item)

    def setup(self, cerebro = None):
        if cerebro is None:
            self.cerebro = bt.Cerebro()
        else:
            self.cerebro = cerebro
        self.data_list = []
        self.strategy_list = []
        self.__setup_broker()
        self.__setup_analyzer()

    def clean_result(self):
        self.result_list = []

    def show_result(self, annual_return = False):
        if len(self.result_list) == 0:
            dbg_info("Not result found.")
            return False
        print(f"{'Symbol':>8} | {'Strategy':>8} | {'Profit':>6} | "
                f"{'Sharpe':>6} | {'VWR':>6} | {'DD':>6} | "
                f"{'SQN':>6} | {'Trades':>6} | ", end = "")
        if annual_return:
            print(f"{'Annual Return -> '} ", end = '')
        print("")
        for each_result in self.result_list:
            dbg_trace(each_result)
            invalid_ratio = 101
            try:
                symbol = ",".join(each_result.get('data', ['']))
                strategy = ",".join(each_result.get('strategy', ['']))
                init_cash = each_result.get('init_cash', 0)
                final_cash = each_result.get('cash', 0)
                profit = final_cash - init_cash
                profit_pct = ((final_cash / init_cash - 1) * 100) if init_cash != 0 else 0

                annual_returns = each_result.get('annual_return', {})
                sharpe = each_result.get('sharpe', invalid_ratio)
                vwr = each_result.get('vwr', invalid_ratio)
                drawdown = each_result.get('drawdown', {}).get('max', {}).get('drawdown', None)
                sqn = each_result.get('sqn', {}).get('sqn', None)
                trades = each_result.get('sqn', {}).get('trades', None)

                if len(symbol) > 5:
                    symbol = 'multi'
                print(f"{symbol:>8} | "
                        f"{strategy:>8} | "
                        f"{safe_format(profit_pct,6,2)} | "
                        f"{safe_format(sharpe,6,2)} | "
                        f"{safe_format(vwr,6,2)} | "
                        f"{safe_format(drawdown,6,2)} | "
                        f"{safe_format(sqn,6,2)} | "
                        f"{trades:>6} | "
                        , end="")
                if annual_return:
                    print(", ".join([f"{year}:{ret:>6.2f}%" for year, ret in annual_returns.items()]), end = '')
                print("")
            except Exception as e:
                dbg_error(e)
                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)

    def add_data(self,product_list , cerebro = None):
        if cerebro is None:
            cerebro = self.cerebro

        for each_product in product_list:
            try:
                df = self.market.get_data(each_product)
                data = bt.feeds.PandasData(dataname=df, fromdate=self.FROM_DATE, todate=self.TO_DATE)

                dbg_trace(f"Add product {each_product}.")

                # Add data to enginee
                cerebro.adddata(data, name=each_product)

                self.data_list.append(each_product)
            except Exception as e:
                dbg_error("Error ticker: ", each_product)
                # self.update_tracking_list(each_product, False)
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                continue
    def eval(self, cerebro = None):
        if cerebro is None:
            cerebro = self.cerebro
            stra_list = cerebro.run()
            self.__analyze(stra_list)


    def add_strategy(self, strategy_list, cerebro = None):
        if cerebro is None:
            cerebro = self.cerebro

        for each_stra in strategy_list:
            dbg_trace(f"Add Straegy: {each_stra}")
            cerebro.addstrategy(each_stra)
            self.strategy_list.append(each_stra)

    # FIXME, remvoe me, it's Legacy API.
    ############################################################################
    def __backtrading(self, cerebro = None):
        if cerebro is None:
            cerebro = self.cerebro

        self.clean_result()
        self.setup(cerebro)

        # # Broker setup
        # self.__setup_broker(cerebro)
        #
        # Add analyzer
        self.__setup_analyzer(cerebro)

        # Do backtesting
        strategy_list = cerebro.run()
        sharpe_ratio = strategy_list[0].analyzers.sharpe.get_analysis().get("sharperatio", None)

        dbg_error("Sharp", sharpe_ratio)
        self.__analyze(strategy_list)
        self.show_result()

        return strategy_list

    def testSingle(self, product_list = None, strategy = None, from_date=datetime(2020, 1, 1), to_date=datetime(2025, 1, 1)):
        # Default testing.
        if strategy is None:
            strategy = self.default_strategy

        if product_list is None:
            product_list = self.default_product_list

        # TODO Impl Test
        ###############################################################
        for each_product in product_list:
            # Init Backtrader
            cerebro = bt.Cerebro()

            df = self.market.get_data(each_product)
            data = bt.feeds.PandasData(dataname=df, fromdate=from_date, todate=to_date)

            # Add data to enginee
            cerebro.adddata(data, name=each_product)

            dbg_info(f"Start running {each_product} with {strategy}.")

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
                        dbg_error("Error ticker: ", each_product)
                        # self.update_tracking_list(each_product, False)
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

