
# system file
import traceback
import time
import threading

# FIXME, may be remove latter
import backtrader as bt
import pandas as pd
from datetime import datetime,timedelta

# Local file
from utility.debug import *
from core.database import *
# from market.provider.yahoo import *
# from market.provider.twse import *
from market.market import *
from backtest.backtest import *
from strategy.strategy import *
from core.tradecli import TDCLI

def sleep_until(target_time: datetime):
    now = datetime.now()
    delta = (target_time - now).total_seconds()
    if delta > 0:
        dbg_trace(f"Sleeping for {delta:.2f} seconds...")
        time.sleep(delta)
    else:
        dbg_trace("Target time already passed.")

class Core:
    def __init__(self):
        # Defines
        self.def_database_name = "trader.db"

        # Flags
        self.flag_core_running = False
        self.flag_heatbeat_running = False
        self.flag_trade_service_running = False

        # Vars
        self.var_threading_delay = 0.1

        # Threading
        self.datasource_service_thread = None
        self.trading_service_thread = None
        self.heatbeat_thread = None

        # class
        self.database = None
        self.tdcli = None
        self.market = None

    def __initcheck(self):
        # Check env setup is okay or not.
        return True
    def __sanitycheck(self):
        # Check sanity check on heart beat okay or not.
        # dbg_info('Sanity Check.')
        pass

    def __heatbeat(self):
        dbg_info('Heatbeat Start.')
        self.flag_heatbeat_running = True

        # TODO Impl heatbeat
        heart_beat_interval_time=10
        while self.flag_core_running and self.flag_heatbeat_running:
            try:
                # dbg_trace('heart beatting every {}s'.format(heart_beat_interval_time))
                self.__sanitycheck()
                time.sleep(heart_beat_interval_time)
            except KeyboardInterrupt:
                dbg_warning("Keyboard Interupt.")
                break;
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)

            finally:
                # Finalize service thread.
                if self.flag_core_running is False or self.flag_trade_service_running is False:
                    dbg_trace('Finalize service thread.')
                    break

                time.sleep(self.var_threading_delay)

        self.flag_heatbeat_running = False
        dbg_warning('Heatbeat End.')
    def __trading_service(self):

        dbg_info('Service Start.')
        self.flag_trade_service_running = True
        # TODO, change it to real life settings.
        service_interval_time=5

        # do the evaluation on every service_interval_time.
        while True:
            try:
                dbg_trace('Trading Service running in every {}s'.format(service_interval_time))

                # TODO, Add broker trading here.
                # backtest = Backtest()
                # # backtest.testSingle(strategy=MovingAverageCrossover)
                # # backtest.testSingle(strategy=BreakoutMomentum)
                # # backtest.testSingle(strategy=BreakoutMomentumEn)
                # # strategy_list = [MovingAverageCrossover, BreakoutMomentum, BreakoutMomentumEn]
                # strategy_list = [MovingAverageCrossover]
                # backtest.testBatch(strategy_list = strategy_list)

                # break
                ###############################################################

                # dbg_info("Tracking List: " + tracking_list.__str__())
                time.sleep(service_interval_time)
            except KeyboardInterrupt:
                dbg_warning("Keyboard Interupt.")
                self.flag_trade_service_running = False
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                self.flag_trade_service_running = False

            finally:
                # Finalize service thread.
                if self.flag_core_running is False or self.flag_trade_service_running is False:
                    dbg_trace('Finalize service thread.')
                    break

                time.sleep(self.var_threading_delay)

        self.flag_trade_service_running = False
        dbg_warning('Service End.')
    def __datasource_service(self):
        dbg_info('Data Srouce Start.')
        self.flag_datasource_service_running = True

        # do the evaluation on every day
        while True:
            try:
                dbg_trace('Update stock info.')

                ###############################################################
                # Update market info here.
                self.market.update_data()
                ###############################################################

                # sleep until next weekday market close time
                now = datetime.now()
                tomorrow = now + timedelta(days=1)
                # Skip weekends (Saturday=5, Sunday=6)
                while tomorrow.weekday() >= 5:  # If Sat or Sun, find next Monday
                    tomorrow += timedelta(days=1)
                target = tomorrow.replace(hour=13, minute=40, second=0, microsecond=0)
                sleep_until(target)
            except KeyboardInterrupt:
                dbg_warning("Keyboard Interupt.")
                self.flag_datasource_service_running = False
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                self.flag_datasource_service_running = False

            finally:
                # Finalize service thread.
                if self.flag_core_running is False or self.flag_datasource_service_running is False:
                    dbg_trace('Finalize service thread.')
                    break

                time.sleep(self.var_threading_delay)

        self.flag_datasource_service_running = False
        dbg_warning('Service End.')
    def initialize(self):
        dbg_info('Core start initialize.')
        try:
            # Checking & init database
            self.database = Database(self.def_database_name)
            self.database.connect()
            self.database.setup()
            # self.database.dump_all()
            self.database.close()
            self.tdcli = TDCLI()
            self.market = Market()
        except Exception as e:
            dbg_error(e)
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            raise
        finally:
            pass

        dbg_info('Core initialized.')
    def start(self):
        dbg_info('Core Start.')
        thread_list = []

        if self.__initcheck() is False:
            dbg_error('Init check fail. Start.')
            return False

        self.flag_core_running = True
        try:
            # Data Thread.
            # Update all market data for analysis later.
            self.datasource_service_thread = threading.Thread(target=self.__datasource_service, daemon=True)
            self.datasource_service_thread.start()
            thread_list.append(self.datasource_service_thread)

            # Trading Thread.
            # Analysis and place order here.
            self.trading_service_thread = threading.Thread(target=self.__trading_service, daemon=True)
            self.trading_service_thread.start()
            thread_list.append(self.trading_service_thread)

            # Monitor Thread
            # Checking thread healthy regularly.
            self.heatbeat_thread = threading.Thread(target=self.__heatbeat, daemon=True)
            # self.heatbeat_thread = threading.Thread(target=self.__heatbeat)
            self.heatbeat_thread.start()
            thread_list.append(self.heatbeat_thread)

            # wait for service start.
            while self.flag_trade_service_running is False or self.flag_heatbeat_running is False:
                dbg_info('Wait for threadings start.')
                time.sleep(0.5)

            # Run CLI
            self.tdcli.run()

            # wait for threading.
            # for each_thread in thread_list:
            #     each_thread.join()

        except KeyboardInterrupt:
            dbg_warning("Keyboard Interupt.")
        except Exception as e:
            dbg_error(e)
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)

            self.flag_core_running = False

        finally:
            dbg_info('Safe exit threading.')
            if self.flag_datasource_service_running and self.datasource_service_thread is not None:
                self.flag_datasource_service_running = False
                self.datasource_service_thread.join()
                self.datasource_service_thread = None

            if self.flag_trade_service_running and self.trading_service_thread is not None:
                self.flag_trade_service_running = False
                self.trading_service_thread.join()
                self.trading_service_thread = None

            if self.flag_heatbeat_running and self.heatbeat_thread is not None:
                self.flag_heatbeat_running = False
                self.heatbeat_thread.join()
                self.heatbeat_thread = None

            self.flag_core_running = False

        dbg_info('Core End.')

    def quit(self):
        dbg_info('Core Quit.')
        # TODO, do final check.

        # if self.database is not None:
        #     self.database.close()

    # FIXME, wait for remove
    def get_tracking_list(self):
        tracking_list = []
        database = None

        database = Database(self.def_database_name)
        database.connect()
        tracking_list = [each_item[0].__str__() for each_item in database.get_tracking_product()]
        database.close()

        return tracking_list
    def update_tracking_list(self, productid, tracking = True):
        # If i need to add this, we need to check if produt is corrent or not.
        tracking_list = []
        database = None

        database = Database(self.def_database_name)
        database.connect()
        database.update_tracking_product(productid, tracking)
        database.close()

        return tracking_list
    def insert_product_list(self, df):
        # If i need to add this, we need to check if produt is corrent or not.
        tracking_list = []
        database = None

        database = Database(self.def_database_name)
        database.connect()

        for _, row in df.iterrows():
            try:
                database.add_product(
                    productid=row["code"],
                    producttype=row["type"],
                    name=row["name"],
                    start=row["start"],
                    market=row["market"],
                    country=row["country"],
                    category=row["category"],
                    tracking=False
                )
            except Exception as e:
                dbg_debug(row["code"], " Add failed.")
                # dbg_debug(e)
                #
                # traceback_output = traceback.format_exc()
                # dbg_debug(traceback_output)
                continue

        # self.add_product('2330', 'stock', '台積電', start='1993-09-05', market='listed', country='TW', Category='半導體業', tracking=True)  
        # database.update_tracking_product(productid, tracking)
        database.close()

        return tracking_list

