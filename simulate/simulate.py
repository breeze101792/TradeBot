# system file
import os
import traceback
from time import sleep as t_sleep
import threading
import shutil

from datetime import datetime
from datetime import time as dt_time
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
import freezegun
# from freezegun.api import real_datetime # Import real_datetime to get actual time

# Local file
from utility.debug import *
from utility.parallelprocessor import ParallelProcessor,analyze_chunk
from core.config import *
from trading.trading import Trading
from broker.brokermanager import BrokerManager
from trading.traderecord import Recorder

class Simulate(threading.Thread):
    def __init__(self, start_time: datetime = None, end_time: datetime = None, product_list: list = None):
        super().__init__()
        self.daemon = True  # Daemonize the thread
        self._is_running = True
        self._is_paused = False # New flag for pausing
        self._pause_event = threading.Event() # Event to signal pausing
        self._auto_pause_disabled_until = None # New: datetime object to temporarily disable auto-pause
        # Calculate the number of threads/processes based on CPU count, with a minimum of 2.
        # This value will be used when initializing ParallelProcessor later.
        num_cpu = os.cpu_count()
        self.parallel_thread = max(2, num_cpu if num_cpu is not None else 2)

        # vars
        self.trading = None
        self.broker_manager = None

        # simulate vars
        self._product_list = product_list

        # settings
        self.broker_type = 'mock'

        # Set default start_time to one year ago at 10:00 AM
        if start_time is None:
            self._start_time = (datetime.now() - relativedelta(months=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        else:
            self._start_time = start_time.replace(hour=10, minute=0, second=0, microsecond=0)

        # Set default end_time to today at 10:00 AM
        if end_time is None:
            self._end_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        else:
            self._end_time = end_time.replace(hour=10, minute=0, second=0, microsecond=0)

        self._simulation_time = self._start_time

    @property
    def simulation_time(self) -> datetime:
        """Get the current simulation time."""
        return self._simulation_time

    @property
    def start_time(self) -> datetime:
        """Get the simulation start time."""
        return self._start_time

    @start_time.setter
    def start_time(self, value: datetime):
        """Set the simulation start time. Note: Changing this while the simulation is running will not re-initialize the mocked time."""
        if self._is_running:
            dbg_warning("Changing start_time while simulation is running may not take effect until restart.")
        self._start_time = value.replace(hour=10, minute=0, second=0, microsecond=0)
        self._simulation_time = self._start_time

    @property
    def end_time(self) -> datetime:
        """Get the simulation end time."""
        return self._end_time

    @end_time.setter
    def end_time(self, value: datetime):
        """Set the simulation end time."""
        self._end_time = value.replace(hour=10, minute=0, second=0, microsecond=0)
    
    @property
    def product_list(self) -> list:
        """Get the list of products for simulation."""
        return self._product_list

    @product_list.setter
    def product_list(self, value: list):
        """Set the list of products for simulation."""
        # could be none, let evaluate.py decide it.
        # if not isinstance(value, list):
        #     raise ValueError("product_list must be a list.")
        self._product_list = value
    
    def prepare(self):
        cfg_mgr = AppConfigManager()
        broker_path = os.path.join(cfg_mgr.get_path('broker'), f'{self.broker_type}')

        if os.path.exists(broker_path):
            if os.path.isfile(broker_path):
                os.remove(broker_path)
                dbg_info(f"Removed existing broker file: {broker_path}")
            elif os.path.isdir(broker_path):
                shutil.rmtree(broker_path)
                dbg_info(f"Removed existing broker directory: {broker_path}")

    def initialize(self):
        # NOTE. this functon need to sync with core.initialize, and enable simulation
        BrokerManager.initialize(broker_type = self.broker_type, simulation=True)
        self.broker_manager = BrokerManager()
        # self.market = Market()
        self.trading = Trading()

        dbg_info('Before simulation, please check the initialize is correct.')

    def finiallize(self):
        self._is_running = False
        self._pause_event.set() # Wake up thraed.

        # wait for thread end.
        while self.is_alive():
            time.sleep(1)

        BrokerManager.finalize()

    def run(self):
        """
        The main method that will be executed when the thread starts.
        Add the simulation logic here.
        """
        loop_interval = 1
        dbg_info("-- Simulation started. --")

        # env setup
        self.prepare()
        self.initialize()
        recorder = Recorder()

        # Start simulation from the specified start_time
        with freeze_time(self.start_time) as frozen_time:
            self._simulation_time = datetime.now()
            while self._is_running and datetime.now() < self.end_time:
                current_sim_time = datetime.now() # This is the simulated time
                # current_real_time = real_datetime.datetime.now() # This is the actual real time
                current_real_time = freezegun.api.real_datetime.now()

                # Automatic pause/continue logic for trading hours (Monday-Friday, 9:00-13:30)
                is_weekday = 0 <= current_real_time.weekday() <= 4 # Monday is 0, Friday is 4
                
                # check before 30 minutes
                trading_start_time = dt_time(8, 30, 0)
                trading_end_time = dt_time(13, 30, 0)
                is_within_trading_hours = trading_start_time <= current_real_time.time() < trading_end_time

                data_update_start_time = dt_time(17, 30, 0)
                data_update_end_time = dt_time(20, 0, 0)
                is_within_data_update_hours = data_update_start_time <= current_real_time.time() < data_update_end_time

                should_pause = is_weekday and (is_within_trading_hours or is_within_data_update_hours)

                if self._auto_pause_disabled_until and current_real_time < self._auto_pause_disabled_until:
                    # ignore checking pause
                    if should_pause or self._is_paused:
                        dbg_debug(f"Auto-pause temporarily disabled. Ignoring restricted hours: {current_sim_time.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    # check the pause
                    if should_pause:
                        if not self._is_paused: # Only pause if not already paused
                            dbg_info(f"Automatically pausing simulation during restricted hours: {current_sim_time.strftime('%Y-%m-%d %H:%M:%S')}")
                            self._pause_event.wait(timeout=1800) # Wait until the event is set, with a 30-minutes timeout
                            self._pause_event.clear() # Clear the event after resuming
                            # self.pause()
                            continue

                    # Check if paused (either manually or automatically)
                    if self._is_paused:
                        dbg_info("Simulation paused. Waiting to continue...")
                        self._pause_event.wait() # Wait until the event is set
                        self._pause_event.clear() # Clear the event after resuming
                        dbg_info("Simulation resumed.")

                dbg_info(f"Simulation loop. Current time: {datetime.now()}")
                # update vars.

                # time check.
                #############################################################
                # we do trading only on monday to friday, so ignore saunday and saturday.
                # Monday is 0, Friday is 4
                is_simulated_weekday = 0 <= current_sim_time.weekday() <= 4 # Monday is 0, Friday is 4

                if is_simulated_weekday:
                    #############################################################
                    # buying eval .
                    try:
                        buying_list = []
                        # FIXME, backtesting lock
                        if False: # Always use parallel processor for now
                            dbg_info('Use parallel Proccessor, we need to resolve the backtest lock.')
                            # Use a lambda to pass the chunk as 'product_list' keyword argument
                            processor = ParallelProcessor(analyze_func=lambda chunk: self.trading.trading_eval(product_list=chunk), num_threads=self.parallel_thread, process_chunk_by_chunk=True, debug_mode = False)
                            # processor = ParallelProcessor(analyze_func=analyze_chunk, num_processes=2, process_chunk_by_chunk=True, debug_mode = True)

                            buying_list = processor.process(self.product_list)

                        else:
                            # Fallback for non-parallel processing (though currently always true)
                            buying_list = self.trading.trading_eval(product_list = self.product_list)

                        if len(buying_list) > 0:
                            dbg_debug(f'Executing buying orders: {buying_list}')
                            self.trading.buying_exec(buying_list)
                        else:
                            dbg_debug('No buying actions triggered in this interval.')
                    except Exception as e:
                        dbg_error(e)
                    
                        traceback_output = traceback.format_exc()
                        dbg_error(traceback_output)

                    # selling eval .
                    try:
                        # NOTE. only do it daily, it may have the difference between core trading flow.
                        # But it only better?
                        selling_list = self.trading.selling_eval()
                        if len(selling_list) > 0:
                            dbg_debug(f'Executing selling orders: {selling_list}')
                            self.trading.selling_exec(selling_list) # Corrected: use selling_list
                        else:
                            dbg_debug('No selling actions triggered in this interval.')

                        # show summary.
                        self.broker_manager.summarize_positions()
                        # self.broker_manager.summarize_transactions()
                        recorder.show_records()
                    except Exception as e:
                        dbg_error(e)
                    
                        traceback_output = traceback.format_exc()
                        dbg_error(traceback_output)

                #############################################################
                t_sleep(loop_interval)
                # Advance time by one day for the next iteration
                frozen_time.tick(relativedelta(days=1))
                self._simulation_time = datetime.now()

        dbg_info("-- End of simulation. --")

    def stop(self):
        """
        Stops the simulation thread gracefully.
        """
        self._is_running = False

    def pause(self):
        """
        Pauses the simulation.
        """
        if self._is_running:
            self._is_paused = True
            dbg_info("Simulation is pausing (it'll take effect on next run.)...")
        else:
            dbg_warning("Simulation is not running, cannot pause.")

    def continue_simulation(self):
        """
        Continues a paused simulation.
        """
        if self._is_paused:
            self._is_paused = False
            self._pause_event.set() # Signal to resume
            dbg_info("Simulation is continuing...")
        else:
            # dbg_warning("Simulation is not paused, cannot continue.")

            # it could also continue the pause set by auto check.
            self._pause_event.set() # Signal to resume

    def disable_auto_pause_for_duration(self, hours: int = 1):
        """
        Temporarily disables automatic pausing for a specified duration.
        """
        self._auto_pause_disabled_until = freezegun.api.real_datetime.now() + relativedelta(hours=hours)
        dbg_info(f"Automatic pausing disabled until {self._auto_pause_disabled_until.strftime('%Y-%m-%d %H:%M:%S')}.")
        self._pause_event.set() # Wake up thraed.

    def time_machine_eval(self, fun_ptr, *args, **kwargs):
        with freeze_time(self._simulation_time) as frozen_time:
            dbg_info(f"Time machine eval: {fun_ptr.__name__}")
            return fun_ptr(*args, **kwargs)
