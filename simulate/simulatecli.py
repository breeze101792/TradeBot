# system file
import traceback
import time
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time # Import freeze_time

# Local file
from utility.debug import *
from utility.cli import *

from broker.brokermanager import BrokerManager
from trading.trading import Trading
from trading.traderecord import Recorder
from simulate.simulate import Simulate
from market.market import Market

class SimulateCLI(CommandLineInterface):
    def __init__(self):
        wellcome_message = """
Welcome to the TradeBot Simulation CLI!

This simulation aims to mimic real trading scenarios.
Please note that this simulation operates on daily data, which may differ
from real-time trading where continuous market information is monitored.
Note. we can only run one simulation on one time.
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

        # configs
        self.regist_cmd("test", self._cmd_test, description="Test simulation settings", arg_list = ['single', 'multiple', 't1', 't50', 'all'], group='config')
        self.regist_cmd("date", self._cmd_date, description="Set simulation start and end dates", arg_list = ['from', 'to', 'week', 'month', 'halfyear', 'year'], group='config')
        self.regist_cmd("product", self._cmd_product, description="Set product list for simulation (e.g., 'product 2330 2331')", arg_list = ['product_id'], group='config')

        # trading
        self.regist_cmd("buy", self._cmd_buy, description="Execute a buy order in simulation", group='trading')
        self.regist_cmd("sell", self._cmd_sell, description="Execute a sell order in simulation", group='trading')
        self.regist_cmd("positions", self._cmd_positions, description="Show current positions in simulation", group='trading')
        self.regist_cmd("transactions", self._cmd_transactions, description="Show transaction history in simulation", group='trading')
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
        if self.simulate:
            print(f"Simulation Status:")
            print(f"  Status: {self.simulate.is_alive()}")
            print(f"  Start Time: {self.simulate.start_time}")
            print(f"  End Time: {self.simulate.end_time}")
            print(f"  Product List: {self.simulate.product_list}")
        else:
            print("Simulation is not running. Cached settings:")
            print(f"  Cached Start Time: {self._cached_start_time}")
            print(f"  Cached End Time: {self._cached_end_time}")
            print(f"  Cached Product List: {self._cached_product_list if self._cached_product_list is not None else 'Using default product list'}")
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
            self.print(f"Simulation from date {self._cached_start_time}, to date {self._cached_end_time}.")
        except Exception as e:
            dbg_error(e)
            dbg_error("date should be like 20200101.")
            return False
        return True
    def _cmd_product(self, args):
        if args['#'] > 0:
            product_ids = []
            for i in range(1, args['#'] + 1):
                product_ids.append(args[str(i)])
            
            self._cached_product_list = product_ids
            self.print(f"Simulation product list set to: {self._cached_product_list}")
            return True
        else:
            dbg_warning("Please provide product IDs. Usage: product <id1> <id2> ...")
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
                self.print(f"Test settings (t1) applied: Start={self._cached_start_time}, End={self._cached_end_time}, Products={self._cached_product_list}")
                return True
                self.print(f"Test settings (single) applied: Start={self._cached_start_time}, End={self._cached_end_time}, Products={self._cached_product_list}")
                return True
            elif args['1'] == 't50':
                # buy & sell.
                self._cached_start_time = (datetime.now() - relativedelta(months=6)).replace(hour=10, minute=0, second=0, microsecond=0)
                self._cached_end_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
                mkt = Market()
                self._cached_product_list = mkt.get_top_product_list(50)
                self.print(f"Test settings (multiple) applied: Start={self._cached_start_time}, End={self._cached_end_time}, Products(len(self._cached_product_list))={self._cached_product_list[:10]}...")
                return True
            elif args['1'] == 'all':
                # buy & sell.
                # half year.
                self._cached_start_time = (datetime.now() - relativedelta(months=6)).replace(hour=10, minute=0, second=0, microsecond=0)
                self._cached_end_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
                mkt = Market()
                self._cached_product_list = mkt.get_data_list()
                self.print(f"Test settings (multiple) applied: Start={self._cached_start_time}, End={self._cached_end_time}, Products(len(self._cached_product_list))={self._cached_product_list[:10]}...")
                return True
        return False
