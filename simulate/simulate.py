# system file
import traceback
from time import sleep as t_sleep
import threading
import shutil

from datetime import datetime, time # Import time
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time
from freezegun.api import real_datetime # Import real_datetime to get actual time

# Local file
from utility.debug import *
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
                current_real_time = real_datetime.now() # This is the actual real time

                # Automatic pause/continue logic for trading hours (Monday-Friday, 9:00-13:30)
                is_weekday = 0 <= current_real_time.weekday() <= 4 # Monday is 0, Friday is 4
                
                trading_start_time = time(9, 0, 0)
                trading_end_time = time(13, 30, 0)
                is_within_trading_hours = trading_start_time <= current_real_time.time() < trading_end_time

                data_update_start_time = time(18, 0, 0)
                data_update_end_time = time(20, 0, 0)
                is_within_data_update_hours = data_update_start_time <= current_real_time.time() < data_update_end_time

                should_pause = is_weekday and (is_within_trading_hours or is_within_data_update_hours)

                if should_pause:
                    if not self._is_paused: # Only pause if not already paused
                        dbg_info(f"Automatically pausing simulation during restricted hours: {current_sim_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        self.pause()
                else:
                    if self._is_paused: # Only continue if currently paused
                        dbg_info(f"Automatically continuing simulation outside restricted hours: {current_sim_time.strftime('%Y-%m-%d %H:%M:%S')}")
                        self.continue_simulation()

                # Check if paused (either manually or automatically)
                if self._is_paused:
                    dbg_info("Simulation paused. Waiting to continue...")
                    self._pause_event.wait() # Wait until the event is set
                    self._pause_event.clear() # Clear the event after resuming
                    dbg_info("Simulation resumed.")

                dbg_info(f"simulation loop. Current time: {datetime.now()}")
                # update vars.

                #############################################################
                # buying eval .
                try:
                    buying_list = self.trading.trading_eval(product_list = self.product_list)
                    if len(buying_list) > 0:
                        dbg_info(f'Executing buying orders: {buying_list}')
                        self.trading.buying_exec(buying_list)
                    else:
                        dbg_info('No buying actions triggered in this interval.')
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
                        dbg_info(f'Executing selling orders: {selling_list}')
                        self.trading.selling_exec(selling_list) # Corrected: use selling_list
                    else:
                        dbg_info('No selling actions triggered in this interval.')

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
            dbg_warning("Simulation is not paused, cannot continue.")

    def time_machine_eval(self, fun_ptr, *args, **kwargs):
        with freeze_time(self._simulation_time) as frozen_time:
            dbg_info(f"Time machine eval: {fun_ptr.__name__}")
            return fun_ptr(*args, **kwargs)

