
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

from backtest.commands import register_backtest_commands
from backtest.btcli import *
from trading.trading import Trading
from trading.traderecord import Recorder
from trading.commands import register_trading_commands

class TDCLI(CommandLineInterface):
    def __init__(self, promote = 'TDCLI'):
        super().__init__(promote=promote)

        ## Vars
        self.market = Market()

        self.cm = AppConfigManager()
        self.history_path = self.cm.get_path('trade_cmd_history')

        ## cmds
        ########################################################################
        self.regist_cmd("trading_config", self.cmd_trade_config, description="Configure global trading settings (e.g., enable/disable buying/selling).", arg_list = ['buy', 'sell', 'enable', 'disable', 'status'], group='trading_private')

        register_trading_commands(self)

        register_backtest_commands(self)

    def cmd_trade_config(self, args):
        trading = Trading()

        if args['#'] == 1:
            if args['1'] == 'status':
                print(f"buying " + "enable" if Trading.BUYING_IGNORE is False else 'disable')
                print(f"selling " + "enable" if Trading.SELLING_IGNORE is False else 'disable')
        elif args['#'] == 2:
            if args['1'] == 'buy':
                if args['2'] == 'enable':
                    Trading.BUYING_IGNORE = False
                elif args['2'] == 'disable':
                    Trading.BUYING_IGNORE = True
                print(f"buying " + "enable" if Trading.BUYING_IGNORE is False else 'disable')
                print(f"selling " + "enable" if Trading.SELLING_IGNORE is False else 'disable')
            elif args['1'] == 'sell':
                if args['2'] == 'enable':
                    Trading.SELLING_IGNORE = False
                elif args['2'] == 'disable':
                    Trading.SELLING_IGNORE = True
                print(f"buying " + "enable" if Trading.BUYING_IGNORE is False else 'disable')
                print(f"selling " + "enable" if Trading.SELLING_IGNORE is False else 'disable')
        return True


