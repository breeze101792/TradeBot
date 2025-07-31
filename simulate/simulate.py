# system file
import os
import traceback
from time import sleep as t_sleep
import multiprocessing
import threading
import shutil
from queue import Empty
import json

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

class Simulate(multiprocessing.Process):
    def __init__(self, start_time: datetime = None, end_time: datetime = None, product_list: list = None):
        super().__init__()
        self._parallel = True
        # daemonic processes are not allowed to have children
        # self.daemon = True  # Daemonize the process
        # Calculate the number of threads/processes based on CPU count, with a minimum of 2.
        # This value will be used when initializing ParallelProcessor later.
        num_cpu = os.cpu_count()
        self.parallel_num = max(2, num_cpu if num_cpu is not None else 2)
        # simulate vars
        self._product_list = product_list
        self.broker_type = 'mock'

        # Process Value
        self._is_running = multiprocessing.Value('b', True)
        self._is_paused = multiprocessing.Value('b', False)
        self._pause_event = multiprocessing.Event()
        self._pause_disabled_until = multiprocessing.Value('d', 0.0)
        self.command_queue = multiprocessing.Queue()

        # Set default start_time to one year ago at 10:00 AM
        if start_time is None:
            _start_time_dt = (datetime.now() - relativedelta(months=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        else:
            _start_time_dt = start_time.replace(hour=10, minute=0, second=0, microsecond=0)
        self._start_time = multiprocessing.Value('d', _start_time_dt.timestamp())

        # Set default end_time to today at 10:00 AM
        if end_time is None:
            _end_time_dt = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        else:
            _end_time_dt = end_time.replace(hour=10, minute=0, second=0, microsecond=0)
        self._end_time = multiprocessing.Value('d', _end_time_dt.timestamp())

        self._simulation_time = multiprocessing.Value('d', self._start_time.value)

        # class vars
        self.trading = None
        self.broker_manager = None

    @property
    def simulation_time(self) -> datetime:
        """Get the current simulation time."""
        return datetime.fromtimestamp(self._simulation_time.value)

    @property
    def start_time(self) -> datetime:
        """Get the simulation start time."""
        return datetime.fromtimestamp(self._start_time.value)

    @start_time.setter
    def start_time(self, value: datetime):
        """Set the simulation start time. Note: Changing this while the simulation is running will not re-initialize the mocked time."""
        if self.is_alive():
            dbg_warning("Changing start_time while simulation is running may not take effect until restart.")
        self._start_time.value = value.replace(hour=10, minute=0, second=0, microsecond=0).timestamp()
        self._simulation_time.value = self._start_time.value

    @property
    def end_time(self) -> datetime:
        """Get the simulation end time."""
        return datetime.fromtimestamp(self._end_time.value)

    @end_time.setter
    def end_time(self, value: datetime):
        """Set the simulation end time."""
        self._end_time.value = value.replace(hour=10, minute=0, second=0, microsecond=0).timestamp()
    
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
    
    def _prepare(self):
        cfg_mgr = AppConfigManager()
        broker_path = os.path.join(cfg_mgr.get_path('broker'), f'{self.broker_type}')

        if os.path.exists(broker_path):
            if os.path.isfile(broker_path):
                dbg_warning(f"An existing broker file: {broker_path}, please fix it.")
            elif os.path.isdir(broker_path):
                dbg_info(f"Start with existing broker directory: {broker_path}")

    def _initialize(self):
        # NOTE. this functon need to sync with core.initialize, and enable simulation
        BrokerManager.initialize(broker_type = self.broker_type, simulation=True)
        self.broker_manager = BrokerManager()
        # self.market = Market()
        self.trading = Trading()

        dbg_info('Before simulation, please check the initialize is correct.')

    def _finiallize(self):
        self._is_running.value = False
        self._pause_event.set() # Wake up process.

        # wait for process end.
        while self.is_alive():
            t_sleep(1)

        BrokerManager.finalize()

    def _config_save(self, file_path: str = None):
        """Saves the current simulation state to a configuration file."""
        cfg_mgr = AppConfigManager()
        sim_config_file = file_path if file_path else os.path.join(cfg_mgr.get_path('broker'), 'simulation_state.json')
        
        state = {
            'start_time': self._start_time.value,
            'end_time': self._end_time.value,
            'simulation_time': self._simulation_time.value,
            'product_list': self._product_list,
            'is_paused': self._is_paused.value,
            'pause_disabled_until': self._pause_disabled_until.value
        }
        
        try:
            with open(sim_config_file, 'w') as f:
                json.dump(state, f, indent=4)
            dbg_info(f"Simulation state saved to {sim_config_file}")
        except Exception as e:
            dbg_error(f"Failed to save simulation state: {e}")
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)

    def _config_load(self, file_path: str = None):
        """Loads the simulation state from a configuration file."""
        cfg_mgr = AppConfigManager()
        sim_config_file = file_path if file_path else os.path.join(cfg_mgr.get_path('broker'), 'simulation_state.json')

        if os.path.exists(sim_config_file):
            try:
                with open(sim_config_file, 'r') as f:
                    state = json.load(f)
                
                self._start_time.value = state.get('start_time', self._start_time.value)
                self._end_time.value = state.get('end_time', self._end_time.value)
                self._simulation_time.value = state.get('simulation_time', self._simulation_time.value)
                self._product_list = state.get('product_list', self._product_list)
                self._is_paused.value = state.get('is_paused', self._is_paused.value)
                self._pause_disabled_until.value = state.get('pause_disabled_until', self._pause_disabled_until.value)
                
                dbg_info(f"Simulation state loaded from {sim_config_file}")
            except Exception as e:
                dbg_error(f"Failed to load simulation state: {e}")
                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
        else:
            dbg_info(f"No existing simulation state found at {sim_config_file}. Starting with default/provided values.")
    def load(self, broker_path: str):
        """
        Loads the simulation state from a specified broker path.
        This function is intended for external calls to resume the simulation from a saved state.
        """
        sim_config_file = os.path.join(broker_path, 'simulation_state.json')
        self._config_load(file_path=sim_config_file)

    def _command_handler(self):
        """Handles commands from the command queue."""
        while self._is_running.value:
            try:
                item = self.command_queue.get(timeout=1)
                if isinstance(item, tuple):
                    command, c_args, c_kwargs = item
                else:
                    command, c_args, c_kwargs = item, [], {}

                if command == 'buy':
                    dbg_info("Manual buy evaluation triggered via command.")
                    self.time_machine_eval(self.trading.trading_eval, *c_args, **c_kwargs)
                elif command == 'sell':
                    dbg_info("Manual sell evaluation triggered via command.")
                    self.time_machine_eval(self.trading.selling_eval, *c_args, **c_kwargs)
                elif command == 'positions':
                    dbg_info("Position summary triggered via command.")
                    self.time_machine_eval(BrokerManager().summarize_positions, *c_args, **c_kwargs)
                elif command == 'transactions':
                    dbg_info("Transaction summary triggered via command.")
                    self.time_machine_eval(BrokerManager().summarize_transactions, *c_args, **c_kwargs)
                elif command == 'trade':
                    dbg_info("Trade record summary triggered via command.")
                    self.time_machine_eval(Recorder().show_records, *c_args, **c_kwargs)
                elif command == 'report':
                    dbg_info("Trade report summary triggered via command.")
                    self.time_machine_eval(Recorder().show_report, *c_args, **c_kwargs)
            except Empty:
                pass  # Check running flag and wait for new commands
            except Exception as e:
                dbg_error(e)
            
                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)

    def _time_iteration(self):
        loop_interval = 0.1
        dbg_info(f"-- Start of time iteration from {self.start_time} to {self.end_time}. --")
        # do time simulation.
        with freeze_time(self.start_time) as frozen_time:
            # self._simulation_time.value = datetime.now().timestamp()
            while self.simulation_time < self.end_time:
                try:
                    # Time control
                    #############################################################
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

                    if self._pause_disabled_until.value > 0 and current_real_time.timestamp() < self._pause_disabled_until.value:
                        # ignore checking pause
                        if should_pause or self._is_paused.value:
                            dbg_debug(f"Auto-pause temporarily disabled. Ignoring restricted hours: {current_sim_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    else:
                        # check the pause
                        if should_pause:
                            if not self._is_paused.value: # Only pause if not already paused
                                dbg_info(f"Automatically pausing simulation during restricted hours: {current_real_time.strftime('%Y-%m-%d %H:%M:%S')}")
                                self._pause_event.wait(timeout=1800) # Wait until the event is set, with a 30-minutes timeout
                                self._pause_event.clear() # Clear the event after resuming
                                # self.pause()
                                continue

                        # Check if paused (either manually or automatically)
                        if self._is_paused.value:
                            dbg_info("Simulation paused. Waiting to continue...")
                            self._pause_event.wait() # Wait until the event is set
                            self._pause_event.clear() # Clear the event after resuming
                            dbg_info("Simulation resumed.")

                    dbg_info(f"Simulation start. Current time: {datetime.now()}")
                    # update vars.

                    ## time check.
                    #############################################################
                    # we do trading only on monday to friday, so ignore saunday and saturday.
                    # Monday is 0, Friday is 4
                    is_simulated_weekday = 0 <= current_sim_time.weekday() <= 4 # Monday is 0, Friday is 4

                    ## Simulation
                    #############################################################
                    if is_simulated_weekday:
                        self._simulate()

                    dbg_info(f"Simulation finished. Current time: {datetime.now()}")
                except KeyboardInterrupt:
                    self._pause_event.clear() # Clear the event after resuming
                    dbg_info(f"get keyboard interupt.")
                except Exception as e:
                    dbg_error(e)
                
                    traceback_output = traceback.format_exc()
                    dbg_error(traceback_output)
                finally:
                    ## Update time variable
                    #############################################################
                    t_sleep(loop_interval)
                    # Advance time by one day for the next iteration
                    frozen_time.tick(relativedelta(days=1))
                    self._simulation_time.value = datetime.now().timestamp()
                    self._config_save() # Save configuration after each daily iteration
        dbg_info("-- End of time iteration. --")

    def _simulate(self):
        #############################################################
        # buying eval .
        try:
            buying_list = []
            # FIXME, backtesting lock
            if self._parallel and (self.product_list is not None and len(self.product_list) > self.parallel_num): # Always use parallel processor for now
                # dbg_info('Use parallel Proccessor')
                # Use a lambda to pass the chunk as 'product_list' keyword argument
                processor = ParallelProcessor(analyze_func=lambda chunk: self.trading.trading_eval(product_list=chunk), num_workers=self.parallel_num, process_chunk_by_chunk=True, debug_mode = False)

                buying_list = processor.process(self.product_list)

            else:
                # dbg_info('Fallback to single Proccessor')
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

        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)

        # summary eval .
        try:
            # show summary.
            self.broker_manager.summarize_positions()
            # self.broker_manager.summarize_transactions()
            recorder = Recorder()
            recorder.show_records()
        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)

        #############################################################
    def run(self):
        """
        The main method that will be executed when the process starts.
        Add the simulation logic here.
        """
        dbg_info("-- Simulation started. --")

        # env setup
        self._prepare()
        self._initialize()

        # command thread.
        command_thread = threading.Thread(target=self._command_handler, daemon=True)
        command_thread.start()

        # Start simulation from the specified start_time
        while self._is_running.value:

            # time iteration.
            dbg_trace(f"simulation time: {self.simulation_time.date()}, end time: {self.end_time.date()}")
            if self.simulation_time.date() != self.end_time.date():
                self._time_iteration()

            t_sleep(1)


    def stop(self):
        """
        Stops the simulation process gracefully.
        """
        self._is_running.value = False

    def pause(self):
        """
        Pauses the simulation.
        """
        # reset pause by pass
        self._pause_disabled_until.value = 0.0

        if self.is_alive():
            self._is_paused.value = True
            dbg_info("Simulation is pausing (it'll take effect on next run.)...")
        else:
            dbg_warning("Simulation is not running, cannot pause.")

    def continue_simulation(self):
        """
        Continues a paused simulation.
        """
        if self._is_paused.value:
            self._is_paused.value = False
            self._pause_event.set() # Signal to resume
            dbg_info("Simulation is continuing...")
        else:
            # dbg_warning("Simulation is not paused, cannot continue.")

            # it could also continue the pause set by auto check.
            self._pause_event.set() # Signal to resume

    def disable_pause_for_duration(self, hours: int = 1):
        """
        Temporarily disables automatic pausing for a specified duration.
        """
        disabled_until_dt = freezegun.api.real_datetime.now() + relativedelta(hours=hours)
        self._pause_disabled_until.value = disabled_until_dt.timestamp()
        dbg_info(f"Automatic pausing disabled until {disabled_until_dt.strftime('%Y-%m-%d %H:%M:%S')}.")
        self._pause_event.set() # Wake up process.

    def time_machine_eval(self, fun_ptr, *args, **kwargs):
        with freeze_time(datetime.fromtimestamp(self._simulation_time.value)) as frozen_time:
            dbg_info(f"Time machine eval: {fun_ptr.__name__}")
            return fun_ptr(*args, **kwargs)
