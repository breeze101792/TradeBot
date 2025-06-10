
# system filejkjk
import traceback
from tabulate import tabulate
import wcwidth # For handling wide characters in tabulate
import threading
import math
import time
# FIXME, may be remove latter
import backtrader as bt
import pandas as pd
from datetime import datetime, timedelta

# Local file
from utility.debug import *
from core.database import *
from core.config import *
from market.market import *
from strategy.strategy import *
from trading.tradecli import TDCLI
from trading.trading import Trading
from trading.evaluate import Evaluate
from broker.brokermanager import BrokerManager

def sleep_with_flag(timeout: float, flag: threading.Event):
    # print(f"Sleeping for up to {timeout} seconds...")
    # This will block up to `timeout` seconds, or return early if flag is set
    interrupted = flag.wait(timeout)
    if interrupted:
        dbg_info("Sleep interrupted by flag!")
        return -1
    # print("Sleep completed.")
def sleep_until_with_flag(target_time: datetime, flag: threading.Event):
    # print(f"Sleeping for up to {target_time} seconds...")
    # This will block up to `target_time` seconds, or return early if flag is set
    now = datetime.now()
    delta = (target_time - now).total_seconds()
    interrupted = flag.wait(delta)
    if interrupted:
        dbg_info("Sleep interrupted by flag!")
        return -1
    # print("Sleep completed.")

def sleep_until(target_time: datetime):
    now = datetime.now()
    delta = (target_time - now).total_seconds()
    if delta > 0:
        dbg_trace(f"Sleeping for {delta:.2f} seconds...")
        time.sleep(delta)
    else:
        dbg_trace("Target time already passed.")

class TradingStatus:
    class Trading:
        target_buying_list = []
        next_wakeup_time = None
        # Potential future state variables can be added here
        # e.g., target_selling_list = [] if needed elsewhere

    class Selling:
        next_wakeup_time = None

    class Datasource:
        next_wakeup_time = None

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

        # FIXME, seperate event for each thread, or it'll be wake up by different thread.
        # or maybe we wrap a service template for it.
        self.stop_event = threading.Event()
        self.trading_status = TradingStatus() # Instantiate the class

        # class
        self.database = None
        self.tdcli = None
        self.market = None
        self.cm = None
        self.trading = None

    def __initcheck(self):
        # Check env setup is okay or not.
        return True
    def __sanitycheck(self, args = None):
        """Check thread running status and system health"""
        if not self.flag_core_running:
            dbg_error("Core is not running!")
            return False
            
        if not self.flag_heatbeat_running:
            dbg_error("Heartbeat service has stopped!")
            return False
            
        if not self.flag_trade_service_running:
            dbg_error("Trading service has stopped!")
            return False
            
        if not self.flag_selling_service_running:
            dbg_error("Selling service has stopped!")
            return False
            
        if not self.flag_datasource_service_running:
            dbg_error("Datasource service has stopped!")
            return False
            
        # Additional health checks can be added here
        return True

    def __update_datasource(self, args = None):
        self.market.update_data(update_trading_day = True)
        return True

    def __heatbeat_service(self):
        dbg_info('Heatbeat Start.')
        self.flag_heatbeat_running = True

        # TODO Impl heatbeat
        heart_beat_interval_time=10
        while self.flag_heatbeat_running:
            try:
                # dbg_trace('heart beatting every {}s'.format(heart_beat_interval_time))
                # TODO, add mail/notification to user of the server issue been found.
                result = self.__sanitycheck()
                if result == False:
                    dbg_error('Service failed.')
                    self.cmd_status()
                sleep_result = sleep_with_flag(heart_beat_interval_time, self.stop_event)
                if sleep_result == -1:
                    break;
                # time.sleep(heart_beat_interval_time)
            except KeyboardInterrupt:
                dbg_warning("Keyboard Interupt.")
                break;
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)

            finally:
                # NOTE. Daemon thread, we do/should not need to stop it.
                # if self.flag_heatbeat_running is False:
                #     dbg_trace('Finalize service thread.')
                #     break

                time.sleep(self.var_threading_delay)

        self.flag_heatbeat_running = False
        dbg_warning('Heatbeat End.')
    def __trading_service(self):

        dbg_info('Trading Service Start.')
        self.flag_trade_service_running = True

        # Reset buying list at the start
        self.trading_status.Trading.target_buying_list = []

        # do the evaluation daily
        while True:
            try:
                # sleeping control
                ###############################################################
                # sleep until next weekday market close time
                # give the time to download first.
                # target = MarketTime.get_next_market_update_time().replace(hour=14, minute=30, second=0, microsecond=0)
                # for development convenience, we set evaluation 4 hours before market open.

                target = None
                current_time = datetime.now().time()

                if current_time > MarketTime.MARKET_UPDATE_TIME:
                    # 15 ~ 24, after market
                    target = MarketTime.get_next_market_open_time() - timedelta(hours=3)
                elif current_time < MarketTime.MARKET_OPEN_TIME :
                    # 0 ~ 8, before market, use one hour early to protect selling service.
                    target = MarketTime.get_next_market_open_time() - timedelta(hours=3)
                else:
                    # 8 ~ 15
                    target = MarketTime.get_next_market_update_time() + timedelta(hours=1)

                self.trading_status.Trading.next_wakeup_time = target # Store wake-up time for eval

                dbg_info(f'Trading Service will wake up at {target}.')
                sleep_result = sleep_until_with_flag(target, self.stop_event)
                if MarketTime.is_trading_day() is False:
                    # goto sleep, since market closed.
                    continue

                self.trading_status.Trading.next_wakeup_time = None # Reset after wake-up or interruption
                if sleep_result == -1:
                    break;
                dbg_info('Running Trading Evaluation')
                # IDEA, do we need to sperate it to buy service?
                # Store the result in the shared status object
                self.trading_status.Trading.target_buying_list = self.trading.trading_eval()

                ###############################################################
                # sleep for trading. put it outside the check to avoid busy loop on this while(if len = 0 will buy pass check).
                # so don't put this sleep inside the check.
                target = MarketTime.get_next_market_open_time().replace(hour=9, minute=0, second=0, microsecond=0)
                self.trading_status.Trading.next_wakeup_time = target # Store wake-up time for buying
                dbg_info(f'Trading Service will wake up at {target}, to buy product.')
                sleep_result = sleep_until_with_flag(target, self.stop_event)

                self.trading_status.Trading.next_wakeup_time = None # Reset after wake-up or interruption
                if sleep_result == -1:
                    break;

                # Check the shared status object
                if len(self.trading_status.Trading.target_buying_list) > 0:
                    # Execute based on the shared status object
                    self.trading.buying_exec(self.trading_status.Trading.target_buying_list)

                # Reset buying list after execution (or if evaluation returned empty)
                self.trading_status.Trading.target_buying_list = []

            except KeyboardInterrupt:
                dbg_warning("Keyboard Interupt.")
                self.flag_trade_service_running = False
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                # self.flag_trade_service_running = False

            finally:
                # Finalize service thread.
                if self.flag_core_running is False or self.flag_trade_service_running is False:
                    dbg_trace('Finalize service thread.')
                    self.flag_core_running = False
                    break

                time.sleep(self.var_threading_delay)

        self.trading_status.Trading.next_wakeup_time = None # Ensure reset on exit
        self.flag_trade_service_running = False
        dbg_warning('Trading Service End.')
    def __selling_service(self):

        dbg_info('Selling Service Start.')
        self.flag_selling_service_running = True

        # wake delay in trading.
        # FIXME, not sure whether it will be banned by back.
        # we may need to find out a way to fix it on data provider.
        # maybe use TWSE for get current stock price continuously
        intra_day_sleep_timedelta = timedelta(seconds=60)

        # do the evaluation daily during market hours
        while True:
            try:
                # Define market close time for today (e.g., 1:20 PM)
                # This assumes MarketTime.get_next_market_open_time() gives the correct date.
                next_market_close_target = MarketTime.get_next_market_close_time().replace(hour=13, minute=20, second=0, microsecond=0)
                market_open_target = next_market_close_target.replace(hour=9, minute=0, second=0, microsecond=0)

                if datetime.now() < next_market_close_target and datetime.now() > market_open_target:
                    dbg_info(f'Selling Service will monitor until {next_market_close_target}.')

                # Intra-day monitoring loop (every 10 minutes until market close)
                while datetime.now() < next_market_close_target and datetime.now() > market_open_target:
                    if not self.flag_core_running or not self.flag_selling_service_running: # Check flags
                        dbg_warning("Core or Selling service stopped during intra-day loop.")
                        break # Exit inner loop

                    dbg_info('Running Selling Evaluation (intra-day)')
                    selling_list = self.trading.selling_eval()
                    if len(selling_list) > 0:
                        dbg_info(f'Executing selling orders (intra-day): {selling_list}')
                        self.trading.selling_exec(selling_list) # Corrected: use selling_list
                    else:
                        dbg_info('No selling actions triggered in this interval.')

                    # Calculate sleep duration for the next 10 minutes, but not past market close
                    now = datetime.now()
                    next_run_time = now + intra_day_sleep_timedelta
                    sleep_duration = 0

                    if next_run_time < next_market_close_target:
                        # Sleep until the next 10-minute mark
                        sleep_duration = (next_run_time - now).total_seconds()
                    else:
                        # Sleep only until market close
                        sleep_duration = (next_market_close_target - now).total_seconds()

                    if sleep_duration <= 0:
                        # If calculation/execution took > 10 mins or we are past close time
                        if now >= next_market_close_target:
                             dbg_info("Market close time reached during check.")
                             break # Exit inner loop, market is closed
                        else:
                             # Minimal sleep if calculation was long but still before close
                             dbg_trace("Calculation took longer than interval, minimal sleep.")
                             sleep_duration = 1 # Sleep briefly before next check

                    # Calculate and store the actual wake-up time for intra-day sleep
                    intra_day_wake_up_time = datetime.now() + timedelta(seconds=sleep_duration)
                    self.trading_status.Selling.next_wakeup_time = intra_day_wake_up_time
                    dbg_trace(f"Selling service sleeping for {sleep_duration:.2f} seconds (until {intra_day_wake_up_time})")
                    sleep_result = sleep_with_flag(sleep_duration, self.stop_event)
                    self.trading_status.Selling.next_wakeup_time = None # Reset after wake-up or interruption
                    if sleep_result == -1:
                        dbg_info("Selling service sleep interrupted during intra-day loop.")
                        break # Exit inner loop if interrupted

                # End of intra-day loop
                if datetime.now() >= next_market_close_target:
                    dbg_info("Selling service finished monitoring for the day (market closed).")
                # If loop exited due to interruption or flag change, it will be handled by the outer loop's finally block

                # sleeping control
                ###############################################################
                # Sleep until next market open time (e.g., 8:55 AM)
                market_open_target = MarketTime.get_next_market_open_time().replace(hour=9, minute=0, second=0, microsecond=0)
                self.trading_status.Selling.next_wakeup_time = market_open_target # Store wake-up time
                dbg_info(f'Selling Service will wake up at {market_open_target} to start intra-day monitoring.')
                sleep_result = sleep_until_with_flag(market_open_target, self.stop_event)
                self.trading_status.Selling.next_wakeup_time = None # Reset after wake-up or interruption
                if sleep_result == -1:
                    dbg_info("Selling service interrupted before market open.")
                    break # Exit outer loop if interrupted before starting

                ###############################################################

            except KeyboardInterrupt:
                dbg_warning("Keyboard Interupt.")
                self.flag_selling_service_running = False
            except Exception as e:
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                # self.flag_selling_service_running = False

            finally:
                # Finalize service thread.
                if self.flag_core_running is False or self.flag_selling_service_running is False:
                    dbg_trace('Finalize service thread.')
                    self.flag_core_running = False
                    break

                time.sleep(self.var_threading_delay)

        self.trading_status.Selling.next_wakeup_time = None # Ensure reset on exit
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
                self.trading_status.Datasource.next_wakeup_time = target # Store wake-up time
                dbg_info(f'Datasource Service will wake up at {target}')
                sleep_result = sleep_until_with_flag(target, self.stop_event)
                self.trading_status.Datasource.next_wakeup_time = None # Reset after wake-up or interruption
                if sleep_result == -1:
                    break;
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
                # self.flag_datasource_service_running = False
            finally:
                # Finalize service thread.
                if self.flag_core_running is False or self.flag_datasource_service_running is False:
                    dbg_trace('Finalize service thread.')
                    self.flag_core_running = False
                    break

                time.sleep(self.var_threading_delay)

        self.trading_status.Datasource.next_wakeup_time = None # Ensure reset on exit
        self.flag_datasource_service_running = False
        dbg_warning('Data Source End.')
    def cmd_status(self, args = None):
        """Prints the current status of the trading core and its services."""
        print("--- Core Status ---")
        ds_next_wakeup = self.trading_status.Datasource.next_wakeup_time
        tr_next_wakeup = self.trading_status.Trading.next_wakeup_time
        sl_next_wakeup = self.trading_status.Selling.next_wakeup_time

        print(f"Core Running               : {self.flag_core_running}")
        print(f"Heartbeat Service Running  : {self.flag_heatbeat_running}")
        print(f"Datasource Service Running : {self.flag_datasource_service_running}" + (f" (Next wake up-> {ds_next_wakeup})" if ds_next_wakeup else ""))
        print(f"Trading Service Running    : {self.flag_trade_service_running}" + (f" (Next wake up-> {tr_next_wakeup})" if tr_next_wakeup else ""))
        print(f"Selling Service Running    : {self.flag_selling_service_running}" + (f" (Next wake up-> {sl_next_wakeup})" if sl_next_wakeup else ""))

        sanity_result = self.__sanitycheck()
        print(f"Sanity Check: {sanity_result}")

        print("\n--- Trading Status ---")
        if self.trading_status.Trading.target_buying_list:
            print("Target Buying List:")
            headers = ["Code", "Name", "Type", "Market", "Category", "Start Date", "Country"]
            table_data = []
            for item_code in self.trading_status.Trading.target_buying_list:
                product_info = self.market.get_data_info(item_code)
                if product_info:
                    table_data.append([
                        product_info.get('code', item_code),
                        product_info.get('name', 'N/A'),
                        product_info.get('type', 'N/A'),
                        product_info.get('market', 'N/A'),
                        product_info.get('category', 'N/A'),
                        product_info.get('start', 'N/A'),
                        product_info.get('country', 'N/A')
                    ])
                else:
                    table_data.append([item_code, "Info not found", "N/A", "N/A", "N/A", "N/A", "N/A"])
            
            if table_data:
                print(tabulate(table_data, headers=headers, tablefmt="grid"))
            else: # Should not happen if target_buying_list is not empty, but good for safety
                print("Target Buying List: Contains items, but no information could be displayed.")
        else:
            print("Target Buying List: Empty")
        # Add more status details here if needed in the future
        print("-------------------")
        return True

    def initialize(self):
        dbg_info('Core start initialize.')
        try:
            self.cm = AppConfigManager()
            BrokerManager.initialize(broker_type = "mock")

            # Checking & init database
            # self.database = Database(self.cm.get_path('tarding_database'))
            # self.database.connect()
            # self.database.setup()
            # # self.database.dump_all()
            # self.database.close()

            self.market = Market()
            self.trading = Trading()
            self.tdcli = TDCLI()

            self.tdcli.regist_cmd("sanity", self.__sanitycheck, description="Run internal health checks for the core system.", group='tools')
            self.tdcli.regist_cmd("update", self.__update_datasource, description="Manually trigger an update of market data from configured sources.", group='tools')
            self.tdcli.regist_cmd("trade", self.trading.trading_eval, description="Do Trading/buy analysis and buy stock.", group='tools')
            self.tdcli.regist_cmd("sell", self.trading.selling_eval, description="Do Selling analysis and sell stock.", group='tools')
            self.tdcli.regist_cmd("status", self.cmd_status, description="Get trading status.", group='tools')
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
            self.datasource_service_thread = threading.Thread(target=self.__datasource_service)
            self.datasource_service_thread.start()
            thread_list.append(self.datasource_service_thread)

            # Trading Thread.
            self.trading_service_thread = threading.Thread(target=self.__trading_service)
            self.trading_service_thread.start()
            thread_list.append(self.trading_service_thread)

            # selling Thread
            self.selling_service_thread = threading.Thread(target=self.__selling_service)
            self.selling_service_thread.start()
            thread_list.append(self.selling_service_thread)

            # Monitor Thread
            # Checking thread healthy regularly.
            self.heatbeat_thread = threading.Thread(target=self.__heatbeat_service, daemon=True)
            # self.heatbeat_thread = threading.Thread(target=self.__heatbeat_service)
            thread_list.append(self.heatbeat_thread)

            # wait for service start.
            while self.flag_selling_service_running is False or self.flag_trade_service_running is False or self.flag_datasource_service_running is False:
                dbg_debug('Wait for threadings start.')
                time.sleep(0.5)

            # start only when all thread is up.
            self.heatbeat_thread.start()
            while self.flag_heatbeat_running is False:
                dbg_debug('Wait for heatbeat threadings start.')
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

            # disable all service flag
            self.flag_core_running = False
            self.flag_trade_service_running = False
            self.flag_selling_service_running = False
            self.flag_datasource_service_running = False
            self.flag_heatbeat_running = False

            # set event to stop sleep.
            self.stop_event.set()

            if self.trading_service_thread is not None:
                self.trading_service_thread.join()
                self.trading_service_thread = None

            if self.selling_service_thread is not None:
                self.selling_service_thread.join()
                self.selling_service_thread = None

            if self.datasource_service_thread is not None:
                self.datasource_service_thread.join()
                self.datasource_service_thread = None

            if self.heatbeat_thread is not None:
                self.heatbeat_thread.join()
                self.heatbeat_thread = None

        dbg_info('Core End.')

    def quit(self):
        dbg_info('Core Quit.')
        # TODO, do final check.
        # self.broker_mgr.finalize()
        BrokerManager.finalize()

        # if self.database is not None:
        #     self.database.close()

