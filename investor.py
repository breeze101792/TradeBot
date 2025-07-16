#!/usr/bin/env python3
# system file
import argparse
import traceback

import matplotlib
from matplotlib import rcParams
from git import Repo

# Local file
from utility.debug import *

from core.core import *
from core.config import *
from backtest.btcli import *
from testutility.testcli import *
from simulate.simulatecli import SimulateCLI

from market.market import *

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

    # broker
    parser.add_argument("--broker", action="store",
        dest="broker_type", default="mock",
        choices=['mock', 'shioaji'],
        help="Select broker for trading, default use mock broker.")

    # trading mode
    parser.add_argument("-m", "--trade-mode", action="store",
        dest="trading_mode", default="trade",
        choices=['backtest', 'test', 'trade', 'simulate'],
        help="Trading mode")

    # Shortcut flag for backtest mode
    parser.add_argument("-b", "--backtest", action="store_const",
        dest="trading_mode", const="backtest", # Set trading_mode to 'backtest' if -b is used
        help="Shortcut to enable backtest mode (equivalent to -m backtest)")

    # Shortcut flag for backtest mode
    parser.add_argument("-t", "--test", action="store_const",
        dest="trading_mode", const="test", # Set trading_mode to 'test' if -t is used
        help="Shortcut to enable test mode (equivalent to -m test)")

    # Shortcut flag for simulate mode
    parser.add_argument("-s", "--simulate", action="store_const",
        dest="trading_mode", const="simulate",
        help="Shortcut to enable simulate mode (equivalent to -m simulate)")

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
        dbg_info(f'Enable {args.trading_mode} mode.')
        cm.set('path.broker', "broker_development")
        cm.set('debug.development', True)
    elif args.trading_mode == 'test':
        dbg_info(f'Enable {args.trading_mode} mode.')
        cm.set('path.broker', "broker_test")
        cm.set('debug.development', True)
    elif args.trading_mode == 'backtest':
        dbg_info(f'Enable {args.trading_mode} mode.')
        cm.set('path.broker', "broker_development")
        cm.set('debug.development', True)
    elif args.trading_mode == 'simulate':
        dbg_info(f'Enable {args.trading_mode} mode.')
        cm.set('path.broker', "simulate")
        cm.set('debug.development', True)
    else:
        ans = input("!!! It's a NOT in development mode, are you sure you want to proceed? (yes/No):")
        if ans in ['y', 'Y', 'yes', 'YES']:
            # Default we use broker type as the broker name.
            broker_subname = args.broker_type
            try:
                repo = Repo('.')  # current directory must be a git repo
                broker_subname = repo.active_branch.name
            except Exception as e:
                dbg_warning(f"Please use under git path. we use git for broker path. now we fallback to use {args.broker_type}, error: {e}")
                traceback_output = traceback.format_exc()
                dbg_warning(traceback_output)

            dbg_warning(f"!!! Real Trading mode with broker: {args.broker_type}")
            cm.set('debug.development', False)
            cm.set('path.broker', f"broker_{broker_subname}")
        else:
            # we should use development flag for it.
            exit(0)

    # env setup.
    setup_matplot()

    # Start core.
    if args.trading_mode == "trade":
        if args.broker_type != 'mcok':
            dbg_info("Starting trading simulation with mock broker.")
        else:
            dbg_warning("Starting trading with {args.broker_type} broker. Use it at your own risk.")
        core = Core()
        try:
            core.initialize(broker_type = args.broker_type)
            core.start()
        except KeyboardInterrupt:
            dbg_error("Keyboard Interupt.")
        except:
            raise
        finally:
            core.finalize()
    elif args.trading_mode == "simulate":
        simulatecli = SimulateCLI()
        simulatecli.run()
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
