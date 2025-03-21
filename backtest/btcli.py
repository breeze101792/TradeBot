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
        super().__init__()

        ## Vars
        self.market = Market()

        self.product_list = ['2330']
        self.strategy_list = [MovingAverageCrossover]
        self.mode = 'single'

        ## cmds
        self.regist_cmd("info", self.cmd_info, description="Show infos.")
        self.regist_cmd("evaluate", self.cmd_evaluate, description="excute backtesting.")

        # Settings
        self.regist_cmd("update", self.cmd_update_database, description="Update local database.")
        self.regist_cmd("add_data", self.cmd_add_data, description="Add product to data list.")
        self.regist_cmd("dataset", self.cmd_dataset, description="Change database, test list sotred", arg_list = ['t20', 'y20', 'y10', 'y05', 'y00'])

        self.regist_cmd("add_strategy", self.cmd_strategy, description="Add strategy.", arg_list = ['MovingAverageCrossover'])
        self.regist_cmd("strategy", self.cmd_strategy, description="Set strategy.", arg_list = ['MovingAverageCrossover'])

        self.regist_cmd("mode", self.cmd_mode, description="Set test mode.", arg_list = ['single', 'batch'])

    def cmd_update_database(self, args):
        self.print("Update local database.")
        self.print("!!! Are you really sure about updating local database.(YES/No, Defaul No.) !!!")
        ans = input()

        if ans == 'YES':
            self.print("Starting update local database.")
            # market = Market()
            # market.update_data()
        else:
            self.print("Do nothing.")
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
        setting_list = ['MovingAverageCrossover']
        if args['#'] == 1:
            if args['1'] in setting_list:
                self.strategy_list=args['1']
                self.print(f"strategy_list : {self.strategy_list}")
                return True
        return False

    def cmd_add_strategy(self, args):
        setting_list = ['MovingAverageCrossover']
        if args['#'] == 1:
            if args['1'] in setting_list:
                self.strategy_list=args['1']
                self.print(f"strategy_list : {self.strategy_list}")
                return True
        return False

    def cmd_mode(self, args):
        setting_list = ['single', 'batch']
        if args['#'] == 1:
            if args['1'] in setting_list:
                self.mode=args['1']
                self.print(f"mode          : {self.mode}")
                return True
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
