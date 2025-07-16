# system file
import traceback
import time

# Local file
from utility.debug import *
from utility.cli import *

from trading.tradecli import TDCLI
from broker.brokermanager import BrokerManager
from trading.trading import Trading
from trading.traderecord import Recorder
from simulate.simulate import Simulate

class SimulateCLI(TDCLI):
    def __init__(self):
        super().__init__(promote='SIM')
        self.simulate = Simulate()

        # register commands
        self.regist_cmd("info", self._cmd_info, description="Show simulation information", group='tools')
        self.regist_cmd("start", self._cmd_start, description="Start the simulation", group='tools')
        self.regist_cmd("stop", self._cmd_stop, description="Stop the simulation", group='tools')
        self.regist_cmd("date", self._cmd_date, description="Set simulation start and end dates", arg_list = ['from', 'to', 'week', 'month'], group='tools')

    def _cmd_info(self, args):
        """
        Displays information about the simulation.
        """
        print(f"Simulation Status:")
        if self.simulate and self.simulate.is_alive():
            print(f"  Status: Running")
            print(f"  Start Time: {self.simulate.start_time}")
            print(f"  End Time: {self.simulate.end_time}")
        else:
            print(f"  Status: Not Running")
        return True

    def _cmd_start(self, args):
        """
        Starts the simulation thread.
        """
        if self.simulate and self.simulate.is_alive():
            print("Simulation is already running.")
        else:
            print("Starting simulation...")
            # Create a new Simulate instance each time it's started
            # as a threading.Thread can only be started once.
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
                    self.simulate.end_time = datetime.today()
                    self.simulate.start_time = datetime.today() - relativedelta(years=int(args['1']))
                elif args['1'] == 'week':
                    self.simulate.end_time = self.simulate.start_time + relativedelta(days=7)
                elif args['1'] == 'month':
                    self.simulate.end_time = self.simulate.start_time + relativedelta(days=30)
                elif args['1'] == 'year':
                    self.simulate.end_time = self.simulate.start_time + relativedelta(years=5)
            elif args['#'] == 2:
                if args['1'] == 'from':
                    if args['2'].isdigit() and int(args['2']) < 100:
                        self.simulate.start_time = datetime.today() - relativedelta(years=int(args['2']))
                    else:
                        self.simulate.start_time = datetime.strptime(args['2'], "%Y%m%d")
                elif args['1'] == 'to':
                    if args['2'].isdigit() and int(args['2']) < 100:
                        self.simulate.end_time = datetime.today() - relativedelta(years=int(args['2']))
                    else:
                        self.simulate.end_time = datetime.strptime(args['2'], "%Y%m%d")
                elif args['1'].startswith('y') and args['2'].isdigit():
                    year = int(args['2'])
                    self.simulate.start_time = datetime(year, 1, 1)
                    self.simulate.end_time = datetime(year, 12, 31)
            self.print(f"Simulation from date {self.simulate.start_time}, to date {self.simulate.end_time}.")
        except Exception as e:
            dbg_error(e)
            dbg_error("date should be like 20200101.")
            return False
        return True
