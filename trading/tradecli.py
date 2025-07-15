
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
from trading.trading import Trading
from trading.traderecord import Recorder

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
        self.regist_cmd("trade", self.cmd_trade, description="Setting trading actions", arg_list = ['buy', 'sell', 'enable', 'disable', 'status'], group='admin')
        self.regist_cmd("positons", self.cmd_positions, description=f"show positions.", arg_list = ['show'], group='trade')
        self.regist_cmd("transactions", self.cmd_transactions, description="show transaction.", arg_list=['year', 'month', 'week', 'day'], group='tools')
        self.regist_cmd("backtest", self.cmd_backtest, description="Enter backtest cli.", group='tools')

    def cmd_trade(self, args):
        trading = Trading()

        if args['#'] == 1:
            if args['1'] == 'status':
                print(f"buying " + "enable" if Trading.BUYING_IGNORE is False else 'disable')
                print(f"selling " + "enable" if Trading.SELLING_IGNORE is False else 'disable')
                recorder = Recorder()
                recorder.show_records()
            else:
                recorder.show_records(symbol=args['1'])
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

        if args['#'] == 1:
            if args['1'] == 'show':
                trade_broker.summarize_positions()
        else:
            trade_broker.summarize_positions()
        return True
    def cmd_transactions(self, args):
        trade_broker = BrokerManager()

        if args['#'] == 1:
            if args['1'] == 'year':
                trade_broker.summarize_transactions('year')
            elif args['1'] == 'month':
                trade_broker.summarize_transactions('month')
            elif args['1'] == 'week':
                trade_broker.summarize_transactions('week')
            elif args['1'] == 'day':
                trade_broker.summarize_transactions('day')
        else:
            trade_broker.summarize_transactions('day')

        return True

