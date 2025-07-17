# system file
import traceback
import time
import threading
import shutil

from datetime import datetime
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

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

        # vars
        self.trading = None
        self.broker_manager = None

        # simulate vars
        if product_list is None:
            self._product_list = ['2330']
        else:
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
        if not isinstance(value, list):
            raise ValueError("product_list must be a list.")
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
        dbg_info("Simulation started.")

        # env setup
        self.prepare()
        self.initialize()
        recorder = Recorder()

        # Start simulation from the specified start_time
        with freeze_time(self.start_time) as frozen_time:
            while self._is_running and datetime.now() < self.end_time:
                dbg_info(f"simulation loop. Current time: {datetime.now()}")
                #############################################################
                # buying eval .
                buying_list = self.trading.trading_eval(product_list = self.product_list)
                if len(buying_list) > 0:
                    dbg_info(f'Executing buying orders: {buying_list}')
                    self.trading.buying_exec(buying_list)
                else:
                    dbg_info('No buying actions triggered in this interval.')

                # selling eval .
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

                #############################################################
                time.sleep(loop_interval)
                # Advance time by one day for the next iteration
                frozen_time.tick(relativedelta(days=1))

        dbg_info("Simulation stopped.")

    def stop(self):
        """
        Stops the simulation thread gracefully.
        """
        self._is_running = False
