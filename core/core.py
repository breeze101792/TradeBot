
# system file
import traceback
import time
import threading

# FIXME, may be remove latter
import backtrader as bt
import pandas as pd
from datetime import datetime

# Local file
from utility.debug import *
from core.database import *
# from market.provider.yahoo import *
# from market.provider.twse import *
from market.market import *
from backtest.backtest import *
from strategy.strategy import *

class Core:
    def __init__(self):
        # Defines
        self.def_database_name = "trader.db"

        # Flags
        self.flag_core_running = False
        self.flag_heatbeat_running = False
        self.flag_service_running = False

        # Vars
        self.var_threading_delay = 0.1

        # Threading
        self.service_thread = None
        self.heatbeat_thread = None

        # class
        self.database = None

    def __initcheck(self):
        # Check env setup is okay or not.
        return True
    def __sanitycheck(self):
        # Check sanity check on heart beat okay or not.
        dbg_info('Sanity Check.')
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
                if self.flag_core_running is False or self.flag_service_running is False:
                    dbg_trace('Finalize service thread.')
                    break

                time.sleep(self.var_threading_delay)

        self.flag_heatbeat_running = False
        dbg_warning('Heatbeat End.')
    def __service(self):

        dbg_info('Service Start.')
        self.flag_service_running = True
        # TODO, change it to real life settings.
        service_interval_time=5

        # do the evaluation on every service_interval_time.
        while True:
            try:
                dbg_trace('Service running in every {}s'.format(service_interval_time))

                backtest = Backtest()
                # backtest.testSingle(strategy=MovingAverageCrossover)
                # backtest.testSingle(strategy=BreakoutMomentum)
                # backtest.testSingle(strategy=BreakoutMomentumEn)
                # strategy_list = [MovingAverageCrossover, BreakoutMomentum, BreakoutMomentumEn]
                strategy_list = [MovingAverageCrossover]
                backtest.testBatch(strategy_list = strategy_list)

                # TODO, Current only one shot test.
                break
                ###############################################################

                # dbg_info("Tracking List: " + tracking_list.__str__())
                time.sleep(service_interval_time)
            except KeyboardInterrupt:
                dbg_warning("Keyboard Interupt.")
                self.flag_service_running = False
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                self.flag_service_running = False

            finally:
                # Finalize service thread.
                if self.flag_core_running is False or self.flag_service_running is False:
                    dbg_trace('Finalize service thread.')
                    break

                time.sleep(self.var_threading_delay)

        self.flag_service_running = False
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
            self.service_thread = threading.Thread(target=self.__service)
            self.service_thread.start()
            thread_list.append(self.service_thread)

            # Monitor Thread
            # self.heatbeat_thread = threading.Thread(target=self.__heatbeat, daemon=True)
            self.heatbeat_thread = threading.Thread(target=self.__heatbeat)
            self.heatbeat_thread.start()
            thread_list.append(self.heatbeat_thread)

            # wait for threading.
            for each_thread in thread_list:
                each_thread.join()

        except KeyboardInterrupt:
            dbg_warning("Keyboard Interupt.")
        except Exception as e:
            dbg_error(e)
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)

            self.flag_core_running = False

        finally:
            if self.flag_service_running and self.service_thread is not None:
                self.flag_service_running = False
                self.service_thread.join()
                self.service_thread = None

            if self.flag_heatbeat_running and self.heatbeat_thread is not None:
                self.flag_heatbeat_running = False
                self.heatbeat_thread.join()
                self.heatbeat_thread = None

            self.flag_core_running = False

        dbg_warning('Core End.')

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

