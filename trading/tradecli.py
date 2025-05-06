
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

from backtest.commands import *
from backtest.btcli import *
from broker.brokermanager import BrokerManager

class TDCLI(CommandLineInterface):
    def __init__(self):
        super().__init__(promote='TDCLI')

        ## Vars
        self.market = Market()

        self.cm = AppConfigManager()
        self.history_path = self.cm.get_path('trade_cmd_history')

        ## cmds
        ########################################################################
        register_commands(self)
        self.regist_cmd("positons", self.cmd_positions, description=f"show positions.", arg_list = ['show'], group='trade')
        self.regist_cmd("transactions", self.cmd_transactions, description="show transaction.", group='tools')
        self.regist_cmd("backtest", self.cmd_backtest, description="Enter backtest cli.", group='tools')
    def cmd_backtest(self, args):
        try:
            btcli = BTCLI()
            btcli.run()
        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return False
        return True

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
    def cmd_transactions(self, args):
        trade_broker = BrokerManager()
        trade_broker.connect()

        if args['#'] == 1:
            if args['1'] == 'year':
                trade_broker.summarize_transactions('year')
            elif args['1'] == 'month':
                trade_broker.summarize_transactions('month')
            elif args['1'] == 'week':
                trade_broker.summarize_transactions('week')
        else:
            trade_broker.summarize_transactions('year')

        trade_broker.disconnect()
        return True

