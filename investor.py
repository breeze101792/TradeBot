#!/usr/bin/env python3
# system file
import argparse

import matplotlib
from matplotlib import rcParams

# Local file
from utility.debug import *
from core.core import *
from core.config import *
from market.market import *
from backtest.btcli import *
from testutility.testcli import *

def setup_matplot():

    # use tornado as webagg
    matplotlib.use('WebAgg')

    # Set WebAgg port before calling plt.show()
    rcParams['webagg.address'] = '0.0.0.0'  # Bind to all interfaces
    rcParams['webagg.port'] = 8888

    # trigger settings.
    import matplotlib.pyplot as plt

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--develoment", dest="develoment",
                    help="develoment mode on!!", action="store_true")

    parser.add_argument("--time-frame", action="store",
        dest="timeframe", default="single",
        choices=['day', 'week'],
        help="Backtesting for with different way to input data. ['single', 'batch']")

    # Product List
    parser.add_argument("-p", "--product-list", action="store",
        dest="product_list", nargs='+',
        help="Specify product id. ")

    # trading mode
    parser.add_argument("-m", "--trade-mode", action="store",
        dest="trading_mode", default="trade",
        choices=['backtest', 'trade', 'test'],
        help="Trading mode")

    # Shortcut flag for backtest mode
    parser.add_argument("-b", "--backtest", action="store_const",
        dest="trading_mode", const="backtest", # Set trading_mode to 'backtest' if -b is used
        help="Shortcut to enable backtest mode (equivalent to -m backtest)")

    # Shortcut flag for backtest mode
    parser.add_argument("-t", "--test", action="store_const",
        dest="trading_mode", const="test", # Set trading_mode to 'test' if -t is used
        help="Shortcut to enable test mode (equivalent to -m test)")

    # enable debug all
    # DebugSetting.setDbgLevel('all')

    # Start config
    cm = AppConfigManager()
    # load default config path
    cm.load(cm.get_path('config'))

    # presetting config
    DebugSetting.setDbgPath(cm.get_path('log'))

    # Start parsing args.
    args = parser.parse_args()
    # DebugSetting.setDbgLevel("all")
    if args.develoment:
        dbg_warning('Enable development mode')
        cm.set('path.broker', "broker_development")
        cm.set('debug.development', True)
    elif args.trading_mode == 'test':
        dbg_warning('Enable development mode')
        cm.set('path.broker', "broker_test")
        cm.set('debug.development', True)
    elif args.trading_mode == 'backtest':
        dbg_warning('Enable development mode')
        cm.set('path.broker', "broker_development")
        cm.set('debug.development', True)
    else:
        ans = input("!!! It's a NOT in development mode, are you sure you want to proceed, or try with development mode.?(y/N, enter to goto development mode.):")
        if ans in ['y', 'Y', 'yes', 'YES']:
            dbg_warning('!!! Real Trading mode !!!')
            cm.set('debug.development', False)
            cm.set('path.broker', "broker")
        else:
            dbg_warning('Enable development mode')
            cm.set('path.broker', "broker_development")
            cm.set('debug.development', True)

    # env setup.
    setup_matplot()

    # Start core.
    if args.trading_mode == "trade":
        dbg_info("Real Trade Not support yet.")
        core = Core()
        try:
            core.initialize()
            core.start()
        except KeyboardInterrupt:
            dbg_error("Keyboard Interupt.")
        except:
            raise
        finally:
            core.finalize()
    elif args.trading_mode == "backtest":
        btcli = BTCLI()
        btcli.run()
    elif args.trading_mode == "test":
        dbg_info("Test Utility Starting.")
        tcli = TestCLI()
        tcli.run()

    dbg_info("Trade Bot finished.")
    cm.save()

if __name__ == '__main__':
    main()
