# system file
import traceback
import time
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time # Import freeze_time
from tabulate import tabulate

# Local file
from utility.debug import *
from utility.cli import *

from core.config import *
from broker.brokermanager import BrokerManager
from trading.trading import Trading
from trading.traderecord import Recorder
from simulate.simulate import Simulate
from market.market import Market

class SimulateCLI(CommandLineInterface):
    def __init__(self):
        cm = AppConfigManager()
        wellcome_message = f"""
Welcome to the TradeBot Simulation CLI!

This simulation aims to mimic real trading scenarios.
Please note that this simulation operates on daily data, which may differ
from real-time trading where continuous market information is monitored.

Simulation path: {cm.get('path.broker')}
        """
        super().__init__(promote='SIM', wellcome_message=wellcome_message)

        self.simulate = None
        # Cached simulation settings
        self._cached_start_time = (datetime.now() - relativedelta(days=7)).replace(hour=10, minute=0, second=0, microsecond=0)
        self._cached_end_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
        self._cached_product_list = None # Default product list

        # register commands
        self.regist_cmd("info", self._cmd_info, description="Show simulation information", group='tools')
        self.regist_cmd("start", self._cmd_start, description="Start the simulation", group='tools')
        self.regist_cmd("stop", self._cmd_stop, description="Stop the simulation", group='tools')
        self.regist_cmd("pause", self._cmd_pause, description="Pause the simulation", group='tools')
        self.regist_cmd("continue", self._cmd_continue, description="Continue a paused simulation", group='tools')

        # configs
        self.regist_cmd("test", self._cmd_test, description="Apply predefined test simulation settings (e.g., 'test single', 'test t50', 'test all')", arg_list = ['single', 'multiple', 't1', 't50', 'all'], group='config')
        self.regist_cmd("date", self._cmd_date, description="Set simulation date range (e.g., 'date 20230101 20231231', 'date week', 'date year 2023')", arg_list = ['from', 'to', 'week', 'month', 'halfyear', 'year'], group='config')
        self.regist_cmd("product", self._cmd_product, description="Set product list for simulation (e.g., 'product 2330 2331', 'product t50', 'product all')", arg_list = ['product_id'], group='config')

        # trading
        self.regist_cmd("buy", self._cmd_buy, description="Execute a buy order in simulation", group='trading')
        self.regist_cmd("sell", self._cmd_sell, description="Execute a sell order in simulation", group='trading')
        self.regist_cmd("positions", self._cmd_positions, description="Show current positions in simulation", group='trading')
        self.regist_cmd("transactions", self._cmd_transactions, description="Show transaction history in simulation (e.g., 'transactions day', 'transactions month')", group='trading')
        self.regist_cmd("trade", self._cmd_trade, description="Show trade records for a specific product and/or strategy (e.g., 'trade 2330' or 'trade strategy=MyStrategy')", arg_list = ['product_id', 'strategy'], group='trading')

    ## Trading, need to mock time.
    ############################################################################
    def _cmd_buy(self, args):
        if self.simulate and self.simulate.trading is not None:
            self.simulate.time_machine_eval(self.simulate.trading.trading_eval)
            return True
        else:
            dbg_warning(f'Please start simulation first.')
            return False
    def _cmd_sell(self, args):
        if self.simulate and self.simulate.trading is not None:
            self.simulate.time_machine_eval(self.simulate.trading.selling_eval)
            return True
        else:
            dbg_warning(f'Please start simulation first.')
            return False
    
    def _cmd_positions(self, args):
        if self.simulate:
            # The summarize_positions method doesn't take arguments
            self.simulate.time_machine_eval(BrokerManager().summarize_positions)
            return True
        else:
            dbg_warning(f'Please start simulation first.')
            return False

    def _cmd_transactions(self, args):
        if self.simulate:
            period = 'day' # Default period
            if args['#'] == 1:
                if args['1'] in ['year', 'month', 'week', 'day']:
                    period = args['1']
            # The summarize_transactions method takes a 'period' argument
            self.simulate.time_machine_eval(BrokerManager().summarize_transactions, period)
            return True
        else:
            dbg_warning(f'Please start simulation first.')
            return False
    def _cmd_trade(self, args):
        if self.simulate:
            symbol = None
            strategy = args.get('strategy', None)
            if args['#'] == 1:
                symbol = args['1']

            self.simulate.time_machine_eval(Recorder().show_records, symbol=symbol, strategy=strategy)
            return True
        else:
            dbg_warning(f'Please start simulation first.')
            return False
    ## End of Trading
    ############################################################################
    def _cmd_info(self, args):
        """
        Displays information about the simulation.
        """
        table_data = []
        headers = ["Setting", "Value"]

        if self.simulate:
            print("Simulation Status:")
            table_data.append(["Status", "Running" if self.simulate.is_alive() else "Stopped"])
            table_data.append(["Start Time", self.simulate.start_time.strftime("%Y-%m-%d %H:%M:%S")])
            table_data.append(["End Time", self.simulate.end_time.strftime("%Y-%m-%d %H:%M:%S")])
            
            # Check for current_time if it exists in Simulate object for more detailed info
            if hasattr(self.simulate, 'current_time'):
                table_data.append(["Current Simulated Time", self.simulate.current_time.strftime("%Y-%m-%d %H:%M:%S")])
            
            product_list_display = "N/A"
            if self.simulate.product_list:
                if len(self.simulate.product_list) > 10:
                    product_list_display = f"{', '.join(self.simulate.product_list[:10])}, ... ({len(self.simulate.product_list)} total)"
                else:
                    product_list_display = ', '.join(self.simulate.product_list)
            table_data.append(["Product List", product_list_display])

            # Potential future expansion: Add more info from BrokerManager or Trading if available
            # For example:
            # if hasattr(self.simulate, 'broker_manager') and self.simulate.broker_manager:
            #     table_data.append(["Broker Balance", f"${self.simulate.broker_manager.get_balance():,.2f}"])
            #     table_data.append(["Total Positions", len(self.simulate.broker_manager.get_positions())])
            # if hasattr(self.simulate, 'trading_instance') and self.simulate.trading_instance:
            #     table_data.append(["Total Trades", self.simulate.trading_instance.get_total_trades()])

            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        else:
            print("Simulation is not running. Cached settings:")
            table_data.append(["Cached Start Time", self._cached_start_time.strftime("%Y-%m-%d %H:%M:%S")])
            table_data.append(["Cached End Time", self._cached_end_time.strftime("%Y-%m-%d %H:%M:%S")])
            
            cached_product_list_display = "Using default product list"
            if self._cached_product_list is not None:
                if len(self._cached_product_list) > 10:
                    cached_product_list_display = f"{', '.join(self._cached_product_list[:10])}, ... ({len(self._cached_product_list)} total)"
                else:
                    cached_product_list_display = ', '.join(self._cached_product_list)
            table_data.append(["Cached Product List", cached_product_list_display])
            
            print(tabulate(table_data, headers=headers, tablefmt="grid"))
        return True

    def _cmd_start(self, args):
        """
        Starts the simulation thread.
        """
        if self.simulate and self.simulate.is_alive():
            print("Simulation is already running. Please stop it first.")
        else:
            print("Starting simulation...")
            # Create a new Simulate instance with cached settings
            self.simulate = Simulate(start_time=self._cached_start_time, end_time=self._cached_end_time)
            self.simulate.product_list = self._cached_product_list # Set product list
            self.simulate.start()
            print("Simulation started.")
        return True

    def _cmd_stop(self, args):
        """
        Stops the simulation thread gracefully.
        """
        if self.simulate and self.simulate.is_alive():
            print("Stopping simulation...")
            self.simulate.stop()
            self.simulate.join() # Wait for the thread to finish
            self.simulate = None # Clear the instance after stopping
            print("Simulation stopped.")
        else:
            print("Simulation is not running.")
        return True

    def _cmd_pause(self, args):
        """
        Pauses the simulation.
        """
        if self.simulate and self.simulate.is_alive():
            self.simulate.pause()
            print("Simulation paused.")
        else:
            print("Simulation is not running or already paused.")
        return True

    def _cmd_continue(self, args):
        """
        Continues a paused simulation.
        """
        if self.simulate and self.simulate.is_alive():
            self.simulate.continue_simulation()
            print("Simulation continued.")
        else:
            print("Simulation is not running or not paused.")
        return True

    def _cmd_date(self, args):
        try:
            if args['#'] == 1:
                if args['1'].isdigit() and int(args['1']) < 100:
                    self._cached_end_time = datetime.today()
                    self._cached_start_time = datetime.today() - relativedelta(years=int(args['1']))
                elif args['1'] == 'week':
                    self._cached_start_time = self._cached_end_time - relativedelta(days=7)
                elif args['1'] == 'month':
                    self._cached_start_time = self._cached_end_time - relativedelta(months=1)
                elif args['1'] == 'halfyear':
                    self._cached_start_time = self._cached_end_time - relativedelta(months=6)
                elif args['1'] == 'year':
                    self._cached_start_time = self._cached_end_time - relativedelta(years=1)
            elif args['#'] == 2:
                if args['1'] == 'from':
                    if args['2'].isdigit() and int(args['2']) < 100:
                        self._cached_start_time = datetime.today() - relativedelta(years=int(args['2']))
                    else:
                        self._cached_start_time = datetime.strptime(args['2'], "%Y%m%d")
                elif args['1'] == 'to':
                    if args['2'].isdigit() and int(args['2']) < 100:
                        self._cached_end_time = datetime.today() - relativedelta(years=int(args['2']))
                    else:
                        self._cached_end_time = datetime.strptime(args['2'], "%Y%m%d")
                elif args['1'].startswith('y') and args['2'].isdigit():
                    year = int(args['2'])
                    self._cached_start_time = datetime(year, 1, 1)
                    self._cached_end_time = datetime(year, 12, 31)
                elif args['1'] == 'year':
                    # ex. year 2024, mean 2024 full year
                    if args['#'] == 2 and args['2'].isdigit():
                        year = int(args['2'])
                        self._cached_start_time = datetime(year, 1, 1, 10, 0, 0, 0)
                        self._cached_end_time = datetime(year, 12, 31, 10, 0, 0, 0)
                    else:
                        dbg_warning("Usage: date year <YYYY>")
                        return False

            self.print(f"Simulation from date {self._cached_start_time}, to date {self._cached_end_time}.")
        except Exception as e:
            dbg_error(e)
            dbg_error("date should be like 20200101.")
            return False
        return True
    def _cmd_product(self, args):

        if args['#'] == 1:
            if args['1'] == 't50':
                mkt = Market()
                self._cached_product_list = mkt.get_top_product_list(50)
                self.print(f"Simulation product list set to top 50 products.")
                return True
            elif args['1'] == 'all':
                mkt = Market()
                self._cached_product_list = mkt.get_data_list()
                self.print(f"Simulation product list set to all available products.")
                return True

        if args['#'] > 0:
            product_ids = []
            for i in range(1, args['#'] + 1):
                product_ids.append(args[str(i)])
            
            self._cached_product_list = product_ids
            self.print(f"Simulation product list set to: {self._cached_product_list}")
            return True
        else:
            dbg_warning("Please provide product IDs or use 't50'/'all'. Usage: product <id1> <id2> ... or product t50 or product all")
            return False

    def _cmd_test(self, args):
        if args['#'] == 1:
            if args['1'] == 'single':
                # buy & sell.
                self._cached_start_time = datetime(2025, 6, 20, 10, 0, 0)
                self._cached_end_time = datetime(2025, 7, 17, 10, 0, 0)
                self._cached_product_list = ['6742'] # Default product list
                self.print(f"Test settings (single) applied: Start={self._cached_start_time}, End={self._cached_end_time}, Products={self._cached_product_list}")
                return True
            elif args['1'] == 'multiple':
                # buy & sell.
                self._cached_start_time = datetime(2025, 6, 20, 10, 0, 0)
                self._cached_end_time = datetime(2025, 7, 17, 10, 0, 0)
                self._cached_product_list = ['6742', '2480', '3661', '6558'] # Default product list
                self.print(f"Test settings (multiple) applied: Start={self._cached_start_time}, End={self._cached_end_time}, Products={self._cached_product_list}")
                return True
            elif args['1'] == 't1':
                # buy & sell.
                self._cached_start_time = datetime(2025, 6, 17, 10, 0, 0)
                self._cached_end_time = datetime(2025, 7, 17, 10, 0, 0)
                self._cached_product_list = ['1210', '1231', '1314', '1337', '1413', '1432', '1460', '1464', '1466', '1472', '1474', '1616', '1708', '2010', '2038', '2109', '2206', '2207', '2211', '2313', '2328', '2459', '2468', '2480', '2520', '2535', '2547', '2597', '2630', '2727', '2832', '2852', '2880', '3018', '3045', '3055', '3167', '3376', '3416', '3543', '3596', '3661', '4104', '4572', '4766', '4904', '5515', '5522', '6128', '6136', '6165', '6209', '6277', '6426', '6472', '6515', '6558', '6669', '6742', '8028', '8222', '9907', '9930']
                self.print(f"Test settings (multiple) applied: Start={self._cached_start_time}, End={self._cached_end_time}, Products({len(self._cached_product_list)})={self._cached_product_list[:10]}...")
                return True
            elif args['1'] == 't50':
                # buy & sell.
                self._cached_start_time = (datetime.now() - relativedelta(months=6)).replace(hour=10, minute=0, second=0, microsecond=0)
                self._cached_end_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
                mkt = Market()
                self._cached_product_list = mkt.get_top_product_list(50)
                self.print(f"Test settings (multiple) applied: Start={self._cached_start_time}, End={self._cached_end_time}, Products({len(self._cached_product_list)})={self._cached_product_list[:10]}...")
                return True
            elif args['1'] == 'all':
                # buy & sell.
                # half year.
                self._cached_start_time = (datetime.now() - relativedelta(months=6)).replace(hour=10, minute=0, second=0, microsecond=0)
                self._cached_end_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
                mkt = Market()
                self._cached_product_list = mkt.get_data_list()
                self.print(f"Test settings (multiple) applied: Start={self._cached_start_time}, End={self._cached_end_time}, Products({len(self._cached_product_list)})={self._cached_product_list[:10]}...")
                return True
        return False
