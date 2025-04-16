#!/usr/bin/env python3
# system file
import argparse

# Local file
from utility.debug import *
from core.core import *
from market.market import *
from backtest.btcli import *

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", dest="debug",
                    help="debug mode on!!", action="store_true")

    # BackTestig data input type
    parser.add_argument("-t", "--test-type", action="store",
        dest="test_type", default="single",
        choices=['single', 'batch'],
        help="Backtesting for with different way to input data. ['single', 'batch']")

    # parser.add_argument("-D", "--data-set", action="store",
    #     dest="test_type", default="default",
    #     choices=['default'],
    #     help="Backtesting for with different data set. ")

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
        dest="trading_mode", default="backtest",
        choices=['backtest', 'faketrade', 'realtrade'],
        help="Trading mode")

    args = parser.parse_args()

    if args.debug:
        DebugSetting.setDbgLevel("all")
        dbg_info('Enable Debug mode')
    else:
        DebugSetting.setDbgLevel("information")
        # DebugSetting.setDbgLevel("all")
        # dbg_info('Enable Debug mode')

    # Start core.
    if args.trading_mode == "faketrade":
        dbg_info("Fake Trade starting .")
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
    elif args.trading_mode == "realtrade":
        dbg_info("Real Trade Not support yet.")
        core = Core()
        try:
            pass
        except KeyboardInterrupt:
            dbg_error("Keyboard Interupt.")
        except:
            raise
        finally:
            core.quit()
    elif args.trading_mode == "backtest":
        btcli = BTCLI()
        btcli.run()

    dbg_info("Trade Bot finished.")

if __name__ == '__main__':
    main()
