import traceback

from utility.debug import *
from trading.trading import Trading
from trading.traderecord import Recorder

from broker.brokermanager import BrokerManager

def register_trading_commands(cli_ins):
    cli_ins.regist_cmd("trade", cmd_trade, description="Manage and view trade records. Use 'trade status [symbol=<SYMBOL>] [duration=<day|week|month|year>]' or 'trade report [period=<day|week|month|year>]'.", arg_list = ['status', 'duration', 'symbol', 'report', 'period'], group='trading')
    cli_ins.regist_cmd("positons", cmd_positions, description=f"Display current open positions.", arg_list = ['show'], group='trading')
    cli_ins.regist_cmd("transactions", cmd_transactions, description="Display historical transactions by time period (year, month, week, day).", arg_list=['year', 'month', 'week', 'day'], group='trading')

def cmd_trade(args):
    recorder = Recorder()

    if args['#'] >= 1:
        subcommand = args['1']
        if subcommand == 'status':
            symbol = args.get('symbol', None)
            duration = args.get('duration', None) # Default to None, let show_records handle its default
            strategy = args.get('strategy', None) # Added strategy if it's ever passed

            recorder.show_records(symbol=symbol, strategy=strategy, duration=duration)
        elif subcommand == 'report':
            period = args.get('period', 'month') # Default to 'month' for report
            recorder.show_report(period=period)
        else:
            dbg_warning(f"Unknown 'trade' subcommand: {subcommand}")
            print("Usage: trade status [symbol=<SYMBOL>] [duration=<day|week|month|year>]")
            print("       trade report [period=<day|week|month|year>]")
    else:
        print("Usage: trade status [symbol=<SYMBOL>] [duration=<day|week|month|year>]")
        print("       trade report [period=<day|week|month|year>]")
    return True
def cmd_positions(args):
    trade_broker = BrokerManager()

    if args['#'] == 1:
        if args['1'] == 'show':
            trade_broker.summarize_positions()
    else:
        trade_broker.summarize_positions()
    return True
def cmd_transactions(args):
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
