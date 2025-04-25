
# system file
import traceback
import threading

import time
# FIXME, may be remove latter
import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta

# Local file
from utility.debug import *
from core.database import *
from core.config import *
# from market.provider.yahoo import *
# from market.provider.twse import *
from market.market import *
from strategy.strategy import *
from trading.tradecli import TDCLI
from trading.evaluate import Evaluate

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
        # Flags
        self.flag_core_running = False
        self.flag_heatbeat_running = False
        self.flag_trade_service_running = False
        self.flag_selling_service_running = False

        # Vars
        self.var_threading_delay = 0.1

        # Threading
        self.datasource_service_thread = None
        self.trading_service_thread = None
        self.selling_service_thread = None
        self.heatbeat_thread = None

        # class
        self.database = None
        self.tdcli = None
        self.market = None
        self.cm = None

    def __initcheck(self):
        # Check env setup is okay or not.
        return True
    def __sanitycheck(self, args = None):
        # Check sanity check on heart beat okay or not.
        # dbg_info('Sanity Check.')
        return True

    def __update_datasource(self, args = None):
        self.market.update_data()
        return True
    def __trading(self, args = None):
        trade_eval = Evaluate()

        # Buyig evaluation.
        buy_list = trade_eval.buying_evaluation()

        # TODO, Place order & save to data base for info/stop_loss price.

        return True
    def __selling(self, args = None):
        trade_eval = Evaluate()

        # TODO, get pos list from broker.
        # pos_list = [{'code':'2330', 'position':5}] 
        pos_list = [] 

        # Selling evaluation.
        sell_dict = trade_eval.selling_evaluation(pos_list)

        # TODO, Place order on real broker
        return True

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
                if self.flag_core_running is False or self.flag_trade_service_running is False or self.flag_selling_service_running is False:
                    dbg_trace('Finalize service thread.')
                    break

                time.sleep(self.var_threading_delay)

        self.flag_heatbeat_running = False
        dbg_warning('Heatbeat End.')
    def __trading_service(self):

        dbg_info('Trading Service Start.')
        self.flag_trade_service_running = True

        # do the evaluation daily
        while True:
            try:
                # sleeping control
                ###############################################################
                # sleep until next weekday market close time
                # give the time to download first.
                target = MarketTime.get_next_market_update_time().replace(hour=14, minute=30, second=0, microsecond=0)
                dbg_info(f'Trading Service will wake up at {target}')
                sleep_until(target)

                ###############################################################
                dbg_info('Running Trading Service')
                self.__selling()

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
        dbg_warning('Trading Service End.')
    def __selling_service(self):

        dbg_info('Selling Service Start.')
        self.flag_selling_service_running = True

        # do the evaluation daily
        while True:
            try:
                # sleeping control
                ###############################################################
                # sleep until next weekday market close time
                # give the time to download first.
                target = MarketTime.get_next_market_open_time()
                dbg_info(f'Selling Service will wake up at {target}')
                sleep_until(target)

                ###############################################################
                dbg_info('Running Selling Service')
                self.__trading()

            except KeyboardInterrupt:
                dbg_warning("Keyboard Interupt.")
                self.flag_selling_service_running = False
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                self.flag_selling_service_running = False

            finally:
                # Finalize service thread.
                if self.flag_core_running is False or self.flag_selling_service_running is False:
                    dbg_trace('Finalize service thread.')
                    break

                time.sleep(self.var_threading_delay)

        self.flag_selling_service_running = False
        dbg_warning('Selling Service End.')
    def __datasource_service(self):
        dbg_info('Data Srouce Start.')
        self.flag_datasource_service_running = True

        # do the evaluation on every day
        while True:
            try:
                # sleeping control
                ###############################################################
                # sleep until next weekday market close time
                # current_time = datetime.now()
                target = MarketTime.get_next_market_update_time()
                dbg_info(f'Datasource Service will wake up at {target}')
                sleep_until(target)
                ###############################################################

                dbg_info('Updating stock info.')
                # Update market info here.
                self.__update_datasource()
                dbg_info('Stock info updated.')
                ###############################################################

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
            self.cm = AppConfigManager()
            # Checking & init database
            self.database = Database(self.cm.get_path('tarding_database'))
            self.database.connect()
            self.database.setup()
            # self.database.dump_all()
            self.database.close()
            self.market = Market()
            self.tdcli = TDCLI()
            self.tdcli.regist_cmd("sanity", self.__sanitycheck, description="Run internal health checks for the core system.", group='tools')
            self.tdcli.regist_cmd("update", self.__update_datasource, description="Manually trigger an update of market data from configured sources.", group='tools')
            self.tdcli.regist_cmd("trade", self.__trading, description="Do Trading/buy analysis and buy stock.", group='tools')
            self.tdcli.regist_cmd("sell", self.__selling, description="Do Selling analysis and sell stock.", group='tools')
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

            self.selling_service_thread = threading.Thread(target=self.__selling_service, daemon=True)
            self.selling_service_thread.start()
            thread_list.append(self.selling_service_thread)

            # Monitor Thread
            # Checking thread healthy regularly.
            self.heatbeat_thread = threading.Thread(target=self.__heatbeat, daemon=True)
            # self.heatbeat_thread = threading.Thread(target=self.__heatbeat)
            self.heatbeat_thread.start()
            thread_list.append(self.heatbeat_thread)

            # wait for service start.
            while self.flag_selling_service_running is False or self.flag_trade_service_running is False or self.flag_heatbeat_running is False:
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

            if self.flag_selling_service_running and self.selling_service_thread is not None:
                self.flag_selling_service_running = False
                self.selling_service_thread.join()
                self.selling_service_thread = None

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

