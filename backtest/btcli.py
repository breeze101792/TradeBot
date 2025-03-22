# system file
import traceback
import time

import backtrader as bt
import pandas as pd
from datetime import datetime

# Local file
from utility.debug import *
from utility.cli import *
from market.market import *

from backtest.backtest import *

class BTCLI(CommandLineInterface):
    def __init__(self):
        # super().__init__(*args, **kwargs)
        super().__init__(promote='backtest')

        ## Vars
        self.market = Market()

        self.product_list = ['2330']
        self.strategy_list = [MovingAverageCrossover]
        self.mode = 'single'
        self.report = None

        ## cmds
        ########################################################################
        self.regist_cmd("info", self.cmd_info, description="Show infos.")
        self.regist_cmd("evaluate", self.cmd_evaluate, description="excute backtesting.")

        # Settings
        self.regist_cmd("update", self.cmd_update_database, description="Update local database.", arg_list = ['all'])
        self.regist_cmd("add_data", self.cmd_add_data, description="Add product to data list.")
        self.total_database_list = ['t20', 'y20', 'y10', 'y05', 'y00']
        self.regist_cmd("dataset", self.cmd_dataset, description=f"Change database, test list stored. {self.total_database_list}", arg_list = self.total_database_list)

        self.total_strategy_list = ['MovingAverageCrossover', 'BreakoutMomentum']
        self.regist_cmd("add_strategy", self.cmd_add_strategy, description=f"Add strategy. {self.total_strategy_list}", arg_list = self.total_strategy_list)
        self.regist_cmd("strategy", self.cmd_strategy, description=f"Set strategy. {self.total_strategy_list}", arg_list = self.total_strategy_list)

        self.total_mode_list = ['single', 'batch']
        self.regist_cmd("mode", self.cmd_mode, description=f"Set test mode. {self.total_mode_list}", arg_list = self.total_mode_list)
        self.regist_cmd("report", self.cmd_report, description=f"Show report of backtest. {self.total_mode_list}", arg_list = self.total_mode_list)

    def cmd_update_database(self, args):
        self.print("Update local database.")
        if args['#'] == 1:
            if args['1'] == 'all':
                self.print("!!! Are you really sure about updating local database.(YES/No, Defaul No. Please enter full word.) !!!")
                ans = input()
                if ans == 'YES':
                    self.market.update_data()
            else:
                self.print(f"!!! Update {args['1']} on local database.(Yes/No, Defaul No.) !!!")
                ans = input()
                if ans == 'YES' or ans == 'Y' or ans == 'y':
                    self.print(f"Update product {args['1']}")
                    self.market.get_data(product_id = args['1'], force_update = True)
            return True
        else:
            self.print(f"product_list  : {self.product_list}")
            self.print("!!! Update above products on local database.(Yes/No, Defaul No.) !!!")
            ans = input()
            if ans == 'YES' or ans == 'Y' or ans == 'y':
                for each_product in self.product_list:
                    self.print(f"Update product {each_product}")
                    self.market.get_data(product_id = each_product, force_update = True)
        return True

    def cmd_info(self, args = None):
        self.print("Info")
        self.print(f"product_list  : {self.product_list}")
        self.print(f"strategy_list : {self.strategy_list}")
        self.print(f"mode          : {self.mode}")
        return True

    def cmd_dataset(self, args):
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
        else:
            for each_arg in range(1, args['#'] + 1):
                self.product_list.append(each_arg)
            self.print(f"product_list  : {self.product_list}")
            return True
        return False

    def cmd_add_data(self, args):
        for each_arg in range(1, args['#'] + 1):
            self.product_list.append(each_arg)
        self.print(f"product_list  : {self.product_list}")
        return True

    def cmd_strategy(self, args):
        # self.total_strategy_list = ['MovingAverageCrossover', 'BreakoutMomentum']
        setting_list = self.total_strategy_list
        if args['#'] == 1:
            if args['1'] == 'MovingAverageCrossover':
                self.strategy_list=[MovingAverageCrossover]
                self.print(f"strategy_list : {self.strategy_list}")
                return True
            elif args['1'] == 'BreakoutMomentum':
                self.strategy_list=[BreakoutMomentum]
                self.print(f"strategy_list : {self.strategy_list}")
                return True
        return False

    def cmd_add_strategy(self, args):
        setting_list = self.total_strategy_list
        if args['#'] == 1:
            if args['1'] == 'MovingAverageCrossover':
                self.strategy_list.append(MovingAverageCrossover)
                self.print(f"strategy_list : {self.strategy_list}")
                return True
            elif args['1'] == 'BreakoutMomentum':
                self.strategy_list.append(BreakoutMomentum)
                self.print(f"strategy_list : {self.strategy_list}")
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

    def cmd_report(self, args):
        if self.report is None:
            self.print("No report found.")
            return False
        return False

    def cmd_evaluate(self, args):
        self.cmd_info()
        backtest = Backtest()
        try:
            if self.mode == 'single':
                backtest.testSingle(strategy=self.strategy_list[0], product_list=self.product_list)
            elif self.mode == 'batch':
                backtest.testBatch(strategy_list = self.strategy_list, product_list = self.product_list)
            else:
                dbg_error(f'Unknown test mode.{self.mode}')
                return False
        except Exception as e:
            dbg_error(e)

            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return False
        return True
