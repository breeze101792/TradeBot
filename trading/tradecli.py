
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
from backtest.commands import *
from strategy.strategy import StrategyManager
from broker.shioajibroker import ShioajiBroker
from broker.brokermanager import BrokerManager

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

        self.cm = AppConfigManager()
        self.history_path = self.cm.get_path('trade_cmd_history')

        ## cmds
        ########################################################################
        register_commands(self)
        self.regist_cmd("positons", self.cmd_positions, description=f"show positions", arg_list = ['show'], group='trade')
    def cmd_positions(self, args):
        trade_broker = BrokerManager()
        trade_broker.connect()

        if args['#'] == 1:
            if args['1'] == 'show':
                trade_broker.summarize_positions()
        else:
            trade_broker.summarize_positions()
        trade_broker.disconnect()
        return True

