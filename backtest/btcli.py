# system file
import traceback
import time

import backtrader as bt
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Local file
from utility.debug import *
from utility.cli import *
from market.market import *

from backtest.backtest import *
from strategy.strategy import StrategyManager
from broker.shioajibroker import ShioajiBroker

class BTCLI(CommandLineInterface):
    def __init__(self):
        super().__init__(promote='backtest')

        ## Vars
        self.market = Market()
        self.strategyMgr = StrategyManager()

        self.product_list = ['2330']
        # self.strategy_list = [MovingAverageCrossover]
        self.strategy_list=[self.strategyMgr.get_strategy_list()[0].NAME]
        self.mode = 'default'
        self.broker = None
        self.backtest = Backtest(self.market)

        ## cmds
        ########################################################################
        # Tools
        self.regist_cmd("info", self.cmd_info, description="Show infos.", group='tools')
        self.regist_cmd("evaluate", self.cmd_evaluate, description="excute backtesting.", group='tools')
        self.regist_cmd("update", self.cmd_update_database, description="Update local database.", arg_list = ['all'], group='tools')
        self.regist_cmd("report", self.cmd_report, description=f"Show report of backtest.", group='tools')
        self.regist_cmd("clean", self.cmd_clean, description=f"Clean report of backtest.", group='tools')

        # Settings
        self.total_mkt_op_list = ['set']
        self.total_mkt_type_list = self.market.get_markget_list()
        self.regist_cmd("market", self.cmd_market, description=f"Change market(data provider). Ops: {self.total_mkt_op_list}, Data:{self.total_mkt_type_list}", arg_list = self.total_mkt_op_list +self.total_mkt_type_list, group='setting')

        self.total_data_list = ['t20', 'y20', 'y10', 'y05', 'y00']
        self.total_data_op_list = ['set', 'add', 'list', 'del']
        self.regist_cmd("data", self.cmd_data, description=f"Change database, test list stored. Ops: {self.total_data_op_list}, Data:{self.total_data_list}", arg_list = self.total_data_list +self.total_data_op_list, group='setting')

        # self.total_strategy_list = ['MovingAverageCrossover', 'BreakoutMomentum']
        self.total_strategy_list = [each_stra.NAME for each_stra in self.strategyMgr.get_strategy_list()]
        self.total_strategy_op_list = ['set', 'add', 'modify', 'list', 'del', 'all']
        # self.regist_cmd("add_strategy", self.cmd_add_strategy, description=f"Add strategy. {self.total_strategy_list}", arg_list = self.total_strategy_list, group='setting')
        self.regist_cmd("strategy", self.cmd_strategy, description=f"Set strategy. Ops: {self.total_strategy_op_list}, Stra:{self.total_strategy_list}", arg_list = self.total_strategy_list + self.total_strategy_op_list, group='setting')
        self.set_date_list = ['to', 'from']
        self.regist_cmd("date", self.cmd_date, description=f"Set date. ex. 20200101", arg_list = self.set_date_list, group='setting')
        self.total_mode_list = ['default', 'single', 'mix']
        self.regist_cmd("mode", self.cmd_mode, description=f"Set test mode. {self.total_mode_list}", arg_list = self.total_mode_list, group='setting')

        self.total_test_cmd_list = ['strategy', 'shioajifake']
        self.regist_cmd("test", self.cmd_test, description=f"Set test commands. cmd:{self.total_test_cmd_list}", arg_list = self.total_test_cmd_list, group='setting')


    def cmd_test(self, args):
        operation_list = self.total_test_cmd_list

        if args['#'] == 1 and args['1'] in operation_list:
            if args['1'] == 'strategy':
                # for easy to trace, set to two month
                self.backtest.TO_DATE = datetime.today()
                self.backtest.FROM_DATE = datetime.today() - relativedelta(months=2)
                dbg_info(f"{datetime.today()},{relativedelta(month=3)}")
                self.strategy_list=['TEST']
                self.cmd_info()
                return True
            elif args['1'] == 'shioajifake':
                self.broker = ShioajiBroker
                return True
        return False
    def cmd_market(self, args):
        operation_list = ['set']
        # market_list = ['twse', 'yahoo']
        market_list = self.total_mkt_type_list
        if args['#'] >= 2 and args['1'] in operation_list:
            if args['1'] == 'set' and args['2'] in market_list:
                self.market.switch_market(args['2'])
                dbg_info(f'switch market to {self.market.get_provider()}')
                return True
        dbg_info(f'market use to {self.market.get_provider()}')
        return False
    def cmd_update_database(self, args):
        self.print("Update local database.")
        if args['#'] == 1:
            if args['1'] == 'all':
                self.print("!!! Are you really sure about updating local database.(YES/No, Defaul No. Please enter full word.) !!!")
                ans = input()
                if ans == 'YES':
                    self.market.update_data()
            else:
                self.print(f"Update product {args['1']}")
                self.market.get_data(product_id = args['1'])
            return True
        else:
            for each_product in self.product_list:
                self.print(f"Update product {each_product}")
                self.market.get_data(product_id = each_product)
        return True

    def cmd_info(self, args = None):
        self.print("## Info")
        self.print("############################################################")
        self.print(f"market        : {self.market.get_provider()}")
        self.print(f"product_list  : {self.product_list}")
        self.print(f"strategy_list : {self.strategy_list}")
        self.print(f"mode          : {self.mode}")
        self.print(f"fromdate      : {self.backtest.FROM_DATE}")
        self.print(f"todate        : {self.backtest.TO_DATE}")
        self.print("############################################################")
        return True

    def cmd_data(self, args):
        # total_data_list = self.total_data_list
        operation_list = self.total_data_op_list
        if args['#'] == 1:
            if args['1'] == 't20':
                self.product_list = self.market.get_top_product_list(20)
            elif args['1'] == 'y20':
                self.product_list = self.market.get_product_list_by_date(start_date = "2020-01-01")
            elif args['1'] == 'y10':
                self.product_list = self.market.get_product_list_by_date(start_date = "2010-01-01")
            elif args['1'] == 'y05':
                self.product_list = self.market.get_product_list_by_date(start_date = "2005-01-01")
            elif args['1'] == 'y00':
                self.product_list = self.market.get_product_list_by_date(start_date = "2000-01-01")
            else:
                self.product_list = [args['1']]
            self.print(f"product_list  : {self.product_list}")
            return True
        elif args['#'] >= 2 and args['1'] in operation_list:
            if args['1'] == 'set' or args['1'] == 'add':
                if args['1'] == 'set':
                    self.product_list = []
                for each_arg in range(2, args['#'] + 1):
                    product_code = args[each_arg.__str__()]
                    if product_code not in self.product_list:
                        self.product_list.append(product_code)
                self.print(f"product_list  : {self.product_list}")
                return True
            elif args['1'] == 'del':
                for each_arg in range(2, args['#'] + 1):
                    product_code = args[each_arg.__str__()]
                    if product_code in self.product_list:
                        self.product_list.remove(product_code)
                self.print(f"product_list  : {self.product_list}")
                return True
            elif args['1'] == 'list':
                self.print(f"product_list  : {self.product_list}")
                return True
        self.print(f"product_list  : {self.product_list}")
        return False

    def cmd_strategy(self, args):
        total_strategy_list = self.total_strategy_list
        operation_list = self.total_strategy_op_list
        if args['#'] == 1 and args['1'] in total_strategy_list:
            # this is dfault action to set strategy
            if args['#'] == 1 and args['1'] in total_strategy_list:
                self.strategy_list=[args['1']]
                self.print(f"strategy_list : {self.strategy_list}")
                return True
            else:
                self.print(f"strategy not found. {args['1']}")
                return True
        elif args['#'] == 1 and args['1'] in operation_list:
            if args['1'] == 'all':
                self.strategy_list = total_strategy_list
                self.print(f"strategy_list : {self.strategy_list}")
                return True
        elif args['#'] >= 2 and args['1'] in operation_list:
            if args['1'] == 'set' or args['1'] == 'add':
                if args['1'] == 'set':
                    self.strategy_list = []
                for each_arg in range(2, args['#'] + 1):
                    each_strategy = args[each_arg.__str__()]
                    if each_strategy not in self.strategy_list and each_strategy in total_strategy_list:
                        self.strategy_list.append(each_strategy)
                    else:
                        self.print(f"Setting fail, Ignore : {each_strategy}")
                self.print(f"strategy_list : {self.strategy_list}")
                return True
            elif args['1'] == 'del':
                for each_arg in range(2, args['#'] + 1):
                    each_strategy = args[each_arg.__str__()]
                    if each_strategy in self.strategy_list and each_strategy in total_strategy_list:
                        self.strategy_list.remove(each_strategy)
                    else:
                        self.print(f"Del fail, Ignore : {each_strategy}")
                self.print(f"strategy_list : {self.strategy_list}")
                return True
            elif args['1'] == 'list':
                self.print(f"Supported strategy : {total_strategy_list}")
                self.print(f"Current strategy : {self.strategy_list}")
                return True
            elif args['1'] == 'modify':
                self.print(f"Function impling.")
                # self.print(f"strategy_list : {self.strategy_list}")
                return True
        return False

    def cmd_mode(self, args):
        setting_list = self.total_mode_list
        if args['#'] == 1:
            if args['1'] in setting_list:
                self.mode=args['1']
                self.print(f"mode          : {self.mode}")
                return True
        return False
    def cmd_date(self, args):
        setting_list = self.set_date_list
        try:
            if args['#'] == 1:
                if int(args['1']) < 100:
                    self.backtest.TO_DATE = datetime.today()
                    self.backtest.FROM_DATE = datetime.today() - relativedelta(years=int(args['1']))
            elif args['#'] == 2:
                if args['1'] == 'from':
                    if int(args['2']) < 100:
                        self.backtest.FROM_DATE = datetime.today() - relativedelta(years=int(args['2']))
                    else:
                        self.backtest.FROM_DATE = datetime.strptime(args['2'], "%Y%m%d")
                elif args['1'] == 'to':
                    if int(args['2']) < 100:
                        self.backtest.TO_DATE = datetime.today() - relativedelta(years=int(args['2']))
                    else:
                        self.backtest.TO_DATE = datetime.strptime(args['2'], "%Y%m%d")
            self.print(f"Set from date {self.backtest.FROM_DATE}, to date {self.backtest.TO_DATE}.")
        except Exception as e:
            dbg_error(e)
            dbg_error("date should be like 20200101.")
            return False
        return True

    def cmd_report(self, args):
        setting_list = ['all']
        if args['#'] == 1:
            if args['1'] == 'all':
                self.backtest.show_result(annual_return=True)
        else:
            self.backtest.show_result(annual_return=True)
        return True

    def cmd_clean(self, args):
        self.backtest.clean_result()
        return True

    def cmd_evaluate(self, args):
        self.cmd_info()
        try:
            self.backtest.clean_result()
            if self.mode == 'default':
                for each_strategy in self.strategy_list:
                    target_strategy = self.strategyMgr.get_strategy_by_name(each_strategy)
                    for each_product in self.product_list:
                        self.backtest.setup(broker=self.broker)
                        self.backtest.add_data([each_product])
                        self.backtest.add_strategy([target_strategy])
                        self.backtest.eval()
                self.backtest.show_result()
            elif self.mode == 'single':
                # self.backtest.testSingle(strategy=self.strategy_list[0], product_list=self.product_list)
                for each_product in self.product_list:
                    self.backtest.setup(broker=self.broker)
                    self.backtest.add_data([each_product])
                    self.backtest.add_strategy([self.strategyMgr.get_strategy_by_name(each_strategy) for each_strategy in self.strategy_list])
                    self.backtest.eval()
                self.backtest.show_result()
            elif self.mode == 'mix':
                # self.backtest.testBatch(strategy_list = self.strategy_list, product_list = self.product_list)
                self.backtest.setup(broker=self.broker)
                self.backtest.add_data(self.product_list)
                self.backtest.add_strategy([self.strategyMgr.get_strategy_by_name(each_strategy) for each_strategy in self.strategy_list])
                self.backtest.eval()
                self.backtest.show_result()
            else:
                dbg_error(f'Unknown test mode.{self.mode}')
                return False
        except Exception as e:
            dbg_error(e)

            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return False
        return True
