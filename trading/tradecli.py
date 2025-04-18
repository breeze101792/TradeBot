
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

class TDCLI(CommandLineInterface):
    def __init__(self):
        super().__init__(promote='TDCLI')

        ## Vars
        self.market = Market()
        self.strategyMgr = StrategyManager(test = 5)

        self.product_list = ['2330']
        # self.strategy_list = [MovingAverageCrossover]
        self.strategy_list=[self.strategyMgr.get_strategy_list()[0].NAME]
        self.mode = 'default'
        self.broker = None
        self.backtest = Backtest(self.market)

        ## cmds
        ########################################################################
        # Tools
        # self.regist_cmd("info", self.cmd_info, description="Show infos.", group='tools')
        # self.regist_cmd("evaluate", self.cmd_evaluate, description="excute backtesting.", group='tools')
        # self.regist_cmd("update", self.cmd_update_database, description="Update local database.", arg_list = ['all'], group='tools')
        # self.regist_cmd("report", self.cmd_report, description=f"Show report of backtest.", group='tools')
        # self.regist_cmd("clean", self.cmd_clean, description=f"Clean report of backtest.", group='tools')
