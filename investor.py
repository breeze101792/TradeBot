#!/usr/bin/env python3
# system file
import argparse

import os
os.environ["MPLBACKEND"] = "Agg"
# WORKAROUND, only set Agg is not use, import it, so it loads.
# import matplotlib.pyplot as plt

# Local file
from utility.debug import *
from core.core import *
from core.config import *
from market.market import *
from backtest.btcli import *
from testutility.testcli import *

def env_setup():
    # For cli drawing, set this to Agg to avoid open window on cli.
    os.environ["MPLBACKEND"] = "Agg"
    import matplotlib.pyplot as plt

    # print("Matplotlib backend:", matplotlib.get_backend())

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
    if args.develoment:
        # DebugSetting.setDbgLevel("all")
        dbg_warning('Enable development mode')
        cm.set('path.broker', "broker_development")
        cm.set('debug.development', True)
    elif args.trading_mode == 'test':
        # DebugSetting.setDbgLevel("all")
        dbg_warning('Enable development mode')
        cm.set('path.broker', "broker_test")
        cm.set('debug.development', True)
    else:
        ans = input("!!! It's a NOT in development mode, are you sure you want to proceed, or try with development mode.?(y/N, enter to goto development mode.):")
        if ans not in ['y', 'Y', 'yes', 'YES']:
            dbg_warning('Disable development mode')
            cm.set('debug.development', False)
            cm.set('path.broker', "broker")
        else:
            dbg_warning('Enable development mode')
            cm.set('path.broker', "broker_development")
            cm.set('debug.development', True)

    # setup env
    env_setup()

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
            core.quit()
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
