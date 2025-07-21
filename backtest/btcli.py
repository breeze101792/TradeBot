# system file
import traceback
import time

import backtrader as bt
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tabulate import tabulate
import json # Added for pretty printing dict

# Local file
from core.config import *
from utility.debug import *
from utility.cli import *
from market.market import *
from market.product.constant import ProductType

from backtest.backtest import *
from strategy.strategy import StrategyManager
from backtest.commands import *
import numpy as np

class BacktestInfo:
    def __init__(self):
        """Initializes BacktestInfo with default values."""
        self._strategy_list = []
        self._product_list = []
        self._mode = ''
        self._from_date = None
        self._to_date = None
        self._strategy_tune_param_grid = {}

    def to_dict(self):
        """Converts the BacktestInfo object to a dictionary for serialization."""
        data = {
            'strategy_list': self._strategy_list,
            'product_list': self._product_list,
            'mode': self._mode,
            'from_date': self._from_date.strftime('%Y-%m-%d %H:%M:%S.%f') if self._from_date else None,
            'to_date': self._to_date.strftime('%Y-%m-%d %H:%M:%S.%f') if self._to_date else None,
            'strategy_tune_param_grid': {k: list(v) if isinstance(v, (np.ndarray, range)) else v for k, v in self._strategy_tune_param_grid.items()},
        }
        return data

    @classmethod
    def from_dict(cls, data):
        """Creates a BacktestInfo object from a dictionary."""
        info = cls()
        info.strategy_list = data.get('strategy_list', [])
        info.product_list = data.get('product_list', [])
        info.mode = data.get('mode', '')
        from_date_str = data.get('from_date')
        to_date_str = data.get('to_date')
        info.from_date = datetime.strptime(from_date_str, '%Y-%m-%d %H:%M:%S.%f') if from_date_str else None
        info.to_date = datetime.strptime(to_date_str, '%Y-%m-%d %H:%M:%S.%f') if to_date_str else None
        info.strategy_tune_param_grid = data.get('strategy_tune_param_grid', {})
        return info

    @property
    def strategy_list(self):
        return self._strategy_list
    @strategy_list.setter
    def strategy_list(self,val):
        self._strategy_list = val

    @property
    def product_list(self):
        """Returns the list of products."""
        return self._product_list

    @product_list.setter
    def product_list(self, val):
        """Sets the list of products."""
        self._product_list = val

    @property
    def mode(self):
        """Returns the current mode."""
        return self._mode

    @mode.setter
    def mode(self, val):
        """Sets the current mode."""
        self._mode = val

    @property
    def from_date(self):
        """Returns the from_date."""
        return self._from_date

    @from_date.setter
    def from_date(self, val):
        """Sets the from_date."""
        self._from_date = val

    @property
    def to_date(self):
        """Returns the to_date."""
        return self._to_date

    @to_date.setter
    def to_date(self, val):
        """Sets the to_date."""
        self._to_date = val

    @property
    def strategy_tune_param_grid(self):
        """Returns the strategy tune parameter grid."""
        return self._strategy_tune_param_grid

    @strategy_tune_param_grid.setter
    def strategy_tune_param_grid(self, val):
        """Sets the strategy tune parameter grid."""
        self._strategy_tune_param_grid = val


class BTCLI(CommandLineInterface):
    def __init__(self):
        super().__init__(promote='backtest')

        ## Vars
        self.def_autoinfo = 'autosave'
        self.cm = AppConfigManager()
        self.market = Market()
        self.strategyMgr = StrategyManager()
        self.backtest = Backtest(self.market)

        self.broker = None
        
        self.bt_info = BacktestInfo()
        self.bt_info.product_list = self.market.get_top_product_list(1)
        self.bt_info.strategy_list = [self.strategyMgr.get_strategy_list()[0].NAME]
        self.bt_info.mode = 'default'
        # Initialize bt_info dates with backtest's default dates
        self.bt_info.from_date = self.backtest.from_date
        self.bt_info.to_date = self.backtest.to_date

        ## post set
        backtest_root_path = self.cm.get_path('backtest')
        self.test_path = os.path.join(backtest_root_path, 'test')
        self.history_path = os.path.join(backtest_root_path, 'command.history')

        ## cmds
        ########################################################################
        # Tools
        self.regist_cmd("info", self.cmd_info, description="Show infos.", group='tools')
        self.regist_cmd("evaluate", self.cmd_evaluate, description="excute backtesting.", group='tools')
        self.regist_cmd("update", self.cmd_update_database, description="Update local database.", arg_list = ['all', 'force'], group='tools')
        self.report_list = ['analysis', 'annual', 'average', 'save', 'draw', 'info']
        self.regist_cmd("report", self.cmd_report, description=f"Show report of backtest.", arg_list = self.report_list, group='tools')
        self.regist_cmd("clean", self.cmd_clean, description=f"Clean report of backtest.", group='tools')

        # Settings
        self.total_mkt_op_list = ['set']
        self.total_mkt_type_list = self.market.get_markget_list()
        self.regist_cmd("market", self.cmd_market, description=f"Change market(data provider). Ops: {self.total_mkt_op_list}, Data:{self.total_mkt_type_list}", arg_list = self.total_mkt_op_list +self.total_mkt_type_list, group='setting')

        self.total_data_list = ['t5', 't10', 't20', 't50', 'y20', 'y10', 'y05', 'y00', 'all', 'etf']
        self.total_data_op_list = ['set', 'add', 'list', 'del', 'number']
        self.regist_cmd("data", self.cmd_data, description=f"Change database, test list stored. Ops: {self.total_data_op_list}, Data:{self.total_data_list}", arg_list = self.total_data_list +self.total_data_op_list, group='setting')

        # self.total_strategy_list = ['MovingAverageCrossover', 'BreakoutMomentum']
        self.total_strategy_list = [each_stra.NAME for each_stra in self.strategyMgr.get_strategy_list([StrategyManager.Level.OFFICIAL,StrategyManager.Level.BETA])]

        self.total_strategy_op_list = ['set', 'add', 'modify', 'list', 'del', 'all', 'tune']
        # self.regist_cmd("add_strategy", self.cmd_add_strategy, description=f"Add strategy. {self.total_strategy_list}", arg_list = self.total_strategy_list, group='setting')
        self.regist_cmd("strategy", self.cmd_strategy, description=f"Set strategy. Ops: {self.total_strategy_op_list}, Stra:{self.total_strategy_list}", arg_list = self.total_strategy_list + self.total_strategy_op_list, group='setting')
        self.set_date_list = ['to', 'from', 'd1', 'd2', 'd3', 'd4', 'd5', 'year']
        self.regist_cmd("date", self.cmd_date, description=f"Set date. ex. 20200101, or 5 Years test d1(from 2000), d2(from 2005), d3(from 2010), d4(from 2015), d5(from 2020).", arg_list = self.set_date_list, group='setting')
        # Forcus on only one mode, to reduce system complexity.
        self.total_mode_list = ['default', 'opt', 'year']
        self.regist_cmd("mode", self.cmd_mode, description=f"Set test mode. {self.total_mode_list}", arg_list = self.total_mode_list, group='setting')

        self.total_stock_cmd_list = ['info', 'data']
        self.regist_cmd("stock", self.cmd_stock, description=f"Show stock info or data. Ops: {self.total_stock_cmd_list}", arg_list = self.total_stock_cmd_list, group='tools')

        self.total_test_cmd_list = ['strategy', 'shioajifake']
        self.regist_cmd("test", self.cmd_test, description=f"Set test commands. cmd:{self.total_test_cmd_list}", arg_list = self.total_test_cmd_list, group='setting')

        self.total_tune_cmd_list = ['set','del', 'clean', 'list']
        self.regist_cmd("tune", self.cmd_tune, description=f"Add tuning params for strategy. Only one strategy at a time(work on opt mode.). cmd:{self.total_tune_cmd_list}", arg_list = self.total_tune_cmd_list, group='setting')

        self.total_attr_cmd_list = ['cash']
        self.regist_cmd("attr", self.cmd_attr, description=f"Set attr of backtest commands. cmd:{self.total_attr_cmd_list}", arg_list = self.total_attr_cmd_list, group='setting')

        self.regist_cmd("save_info", self.cmd_save_info, description="Save current backtest info to a JSON file.", group='tools')
        self.regist_cmd("load_info", self.cmd_load_info, description="Load backtest info from a JSON file.", group='tools')

        ## utility
        register_backtest_commands(self)

    def cmd_test(self, args):
        operation_list = self.total_test_cmd_list

        if args['#'] == 1 and args['1'] in operation_list:
            if args['1'] == 'strategy':
                # for easy to trace, set to two month
                # self.backtest.to_date = datetime.today()
                # self.backtest.from_date = datetime.today() - relativedelta(months=2)
                # dbg_info(f"{datetime.today()},{relativedelta(month=3)}")
                self.product_list = ['2303', '6505', '1101', '1301', '1303', '1326']
                self.strategy_list=['MultiSignal']
                self.cmd_info()
                return True
            elif args['1'] == 'shioajifake':
                self.broker = ShioajiBroker
                return True
        return False
    def cmd_stock(self, args):
        self.total_stock_cmd_list = ['info', 'data']
        opt_list = self.total_stock_cmd_list

        product_id = None
        operation = None

        if args['#'] == 1:
            if args['1'] == 'info' or args['1'] == 'data':
                operation = args['1']
                current_product_list = self.bt_info.product_list
                if current_product_list: # Use the first product in the list if no specific ID is given
                    product_id = current_product_list[0]
                else:
                    self.print("No product selected. Please set a product first or specify one.")
                    return False
            else:
                self.print('usage: stock [info|data] [product_id]')
                return False
        elif args['#'] == 2 and args['1'] in opt_list:
            operation = args['1']
            product_id = args['2']
        else:
            self.print('usage: stock [info|data] [product_id]')
            return False

        if operation == 'info':
            stock_info = self.market.get_data_info(product_id)
            if stock_info:
                self.print(f"\n## Stock Info for {product_id}")
                table_data = []
                for key, value in stock_info.items():
                    table_data.append([key, value])
                headers = ["Attribute", "Value"]
                self.print(tabulate(table_data, headers=headers, tablefmt="pretty", numalign="left", stralign="left"))
            else:
                self.print(f"Could not retrieve info for product ID: {product_id}")
        elif operation == 'data':
            # Ensure from_date and to_date are set for data retrieval
            from_date = self.bt_info.from_date
            to_date = self.bt_info.to_date

            if not from_date or not to_date:
                self.print("Please set 'from' and 'to' dates using the 'date' command before requesting data.")
                return False

            self.print(f"Fetching data for {product_id} from {from_date.strftime('%Y-%m-%d')} to {to_date.strftime('%Y-%m-%d')}")
            stock_data_df = self.market.get_data(product_id=product_id, start_date=from_date.date(), end_date=to_date.date())

            if stock_data_df is not None and not stock_data_df.empty:
                self.print(f"\n## Historical Data for {product_id} (Head)")
                self.print(tabulate(stock_data_df.head(), headers='keys', tablefmt="pretty"))
                self.print(f"\n## Historical Data for {product_id} (Tail)")
                self.print(tabulate(stock_data_df.tail(), headers='keys', tablefmt="pretty"))
                self.print(f"\nTotal {len(stock_data_df)} records.")
            else:
                self.print(f"No historical data found for product ID: {product_id} in the specified date range.")
        return True
    def cmd_attr(self, args):
        attr_list = self.total_attr_cmd_list

        if args['#'] == 1:
            if args['1'] == 'cash':
                self.print(f"init cash: {self.backtest.init_cash}")
        elif args['#'] == 2 and args['1'] in attr_list:
            if args['1'] == 'cash':
                self.backtest.init_cash = int(args['2'])
        else:
            self.print('usage: attr [attriable name] [attr value]')
            return False
        return True
    def cmd_market(self, args):
        operation_list = ['set']
        # market_list = ['twse', 'yahoo']
        market_list = self.total_mkt_type_list
        if args['#'] >= 2 and args['1'] in operation_list:
            if args['1'] == 'set' and args['2'] in market_list:
                self.market.switch_market(args['2'])
                dbg_info(f'switch market to {self.market.get_provider()}')
                return True
        dbg_info(f'market use to {self.market.get_provider()}')
        return False
    def cmd_update_database(self, args):
        self.print("Update local database.")
        current_product_list = self.bt_info.product_list
        current_market = self.market

        if args['#'] == 1:
            if args['1'] == 'all':
                self.print("!!! Are you really sure about updating local database.(YES/No, Defaul No. Please enter full word.) !!!")
                ans = input()
                if ans == 'YES':
                    current_market.update_data()
            elif args['1'] == 'force':
                current_market.update_data(product_list = current_product_list, force_update = True)
            else:
                self.print(f"Update product {args['1']}")
                current_market.update_data(product_list = [args['1']])
        elif args['#'] == 2:
            if args['1'] == 'force':
                if args['2'] == 'all':
                    self.print("!!! Are you really sure about FORCE updating local database.(YES/No, Defaul No. Please enter full word.) !!!")
                    ans = input()
                    if ans == 'YES':
                        current_market.update_data(force_update = True)
                else:
                    self.print(f"Force update product {args['2']}")
                    current_market.update_data(product_list = [args['2']], force_update = True)
        else:
            current_market.update_data(product_list = current_product_list)
        return True

    def cmd_info(self, args = None):
        table_data = []

        table_data.append(["market", self.market.get_provider()])

        current_mode = self.bt_info.mode
        current_strategy_list = self.bt_info.strategy_list
        current_product_list = self.bt_info.product_list

        # Handle current_product_list display
        if len(current_product_list) > 20:
            product_string = f"{current_product_list[:20]} ... (Total: {len(current_product_list)})"
        else:
            product_string = f"{current_product_list} (Total: {len(current_product_list)})"
        table_data.append(["product_list", product_string])

        table_data.append(["strategy_list", current_strategy_list])
        table_data.append(["mode", current_mode])
        table_data.append(["init cash", self.backtest.init_cash])
        table_data.append(["fromdate", self.bt_info.from_date])
        table_data.append(["todate", self.bt_info.to_date])

        headers = ["Info Item", "Value"]

        # Print the table using tabulate with left alignment
        self.print(tabulate(table_data, headers=headers, tablefmt="pretty", numalign="left", stralign="left"))

        # Print tune params separately if in opt mode
        if current_mode == 'opt':
            self.print("\n## Tune Parameters") # Add a header for tune params
            # Use json.dumps for pretty printing the dictionary
            self.print(self.bt_info.strategy_tune_param_grid)

        return True

    def cmd_data(self, args):
        # total_data_list = self.total_data_list
        operation_list = self.total_data_op_list
        product_list = self.bt_info.product_list
        if args['#'] == 1:
            if args['1'] == 't5':
                product_list = self.market.get_top_product_list(5)
            elif args['1'] == 't10':
                product_list = self.market.get_top_product_list(10)
            elif args['1'] == 't20':
                product_list = self.market.get_top_product_list(20)
            elif args['1'] == 't50':
                product_list = self.market.get_top_product_list(50)
            elif args['1'] == 'y20':
                product_list = self.market.get_product_list_by_date(start_date = "2020-01-01")
            elif args['1'] == 'y10':
                product_list = self.market.get_product_list_by_date(start_date = "2010-01-01")
            elif args['1'] == 'y05':
                product_list = self.market.get_product_list_by_date(start_date = "2005-01-01")
            elif args['1'] == 'y00':
                product_list = self.market.get_product_list_by_date(start_date = "2000-01-01")
            elif args['1'] == 'all':
                product_list = self.market.get_data_list()
            elif args['1'] == 'etf':
                product_list = self.market.get_data_list(product_type = ProductType.ETF)
            else:
                product_list = [args['1']]
            self.print(f"product_list({len(product_list)}) : {product_list}")
            self.bt_info.product_list = product_list
            return True
        elif args['#'] >= 2 and args['1'] in operation_list:
            if args['1'] == 'set' or args['1'] == 'add':
                if args['1'] == 'set':
                    product_list = []
                for each_arg in range(2, args['#'] + 1):
                    product_code = args[each_arg.__str__()]
                    if product_code not in product_list:
                        product_list.append(product_code)
                self.print(f"product_list({len(product_list)}) : {product_list}")
                self.bt_info.product_list = product_list
                return True
            elif args['1'] == 'del':
                for each_arg in range(2, args['#'] + 1):
                    product_code = args[each_arg.__str__()]
                    if product_code in product_list:
                        product_list.remove(product_code)
                self.print(f"product_list({len(product_list)}) : {product_list}")
                self.bt_info.product_list = product_list
                return True
            elif args['1'] == 'list':
                self.print(f"product_list({len(product_list)}) : {product_list}")
                return True
            elif args['1'] == 'number':
                product_list = self.market.get_data_list()[:int(args['2'])]
                self.print(f"product_list({len(product_list)}) : {product_list}")
                self.bt_info.product_list = product_list
                return True

        self.print(f"product_list({len(product_list)}) : {product_list}")
        return False

    def cmd_strategy(self, args):
        total_strategy_list = self.total_strategy_list
        operation_list = self.total_strategy_op_list
        current_strategy_list = self.bt_info.strategy_list
        if args['#'] == 1 and args['1'] in total_strategy_list:
            # this is dfault action to set strategy
            if args['#'] == 1 and args['1'] in total_strategy_list:
                self.bt_info.strategy_list = [args['1']]
                self.print(f"strategy_list : {self.bt_info.strategy_list}")
                return True
            else:
                self.print(f"strategy not found. {args['1']}")
                return True
        elif args['#'] == 1 and args['1'] in operation_list:
            if args['1'] == 'all':
                self.bt_info.strategy_list = total_strategy_list
                self.print(f"strategy_list : {self.bt_info.strategy_list}")
                return True
        elif args['#'] >= 2 and args['1'] in operation_list:
            if args['1'] == 'set' or args['1'] == 'add':
                if args['1'] == 'set':
                    current_strategy_list = []
                for each_arg in range(2, args['#'] + 1):
                    each_strategy = args[each_arg.__str__()]
                    if each_strategy not in current_strategy_list and each_strategy in total_strategy_list:
                        current_strategy_list.append(each_strategy)
                    else:
                        self.print(f"Setting fail, Ignore : {each_strategy}")
                self.bt_info.strategy_list = current_strategy_list
                self.print(f"strategy_list : {self.bt_info.strategy_list}")
                return True
            elif args['1'] == 'del':
                for each_arg in range(2, args['#'] + 1):
                    each_strategy = args[each_arg.__str__()]
                    if each_strategy in current_strategy_list and each_strategy in total_strategy_list:
                        current_strategy_list.remove(each_strategy)
                    else:
                        self.print(f"Del fail, Ignore : {each_strategy}")
                self.bt_info.strategy_list = current_strategy_list
                self.print(f"strategy_list : {self.bt_info.strategy_list}")
                return True
            elif args['1'] == 'list':
                self.print(f"Supported strategy : {total_strategy_list}")
                self.print(f"Current strategy : {self.bt_info.strategy_list}")
                return True
            elif args['1'] == 'modify':
                self.print(f"Function impling.")
                # self.print(f"strategy_list : {self.strategy_list}")
                return True
            elif args['1'] == 'tune':
                self.print(f"Function impling.")
        return False
    def cmd_tune(self, args):
        total_tune_list = self.total_tune_cmd_list
        
        current_strategy_list = self.bt_info.strategy_list
        if len(current_strategy_list) == 0:
            dbg_warning('No strategy found on list.')
            return False
        strategy_ins = self.strategyMgr.get_strategy_by_name(current_strategy_list[0])
        if args['#'] == 0:
            self.print(f"Current Paramte:{self.bt_info.strategy_tune_param_grid}")
            # self.print(f"Support Paramte:")
            strategy_ins.dump_params(strategy_ins)
            return True
        
        first_arg = args['1']
        
        if first_arg not in total_tune_list:
            self.print(f"Unknow options, supported operation: {total_tune_list}")
            return False
        
        if first_arg == 'list':
            self.print(f"Current Paramte:{self.bt_info.strategy_tune_param_grid}")
            strategy_ins.dump_params(strategy_ins)
            return True
        elif first_arg == 'set':
            # dbg_info(args['@'])
            if args['#'] < 3:
                self.print("Usage: strategy set [param name] [value]")
                self.print("Usage: strategy set [param name] [start] [end] [step]")
                return False
            param_name = args['2']

            # check if there is a params inside strategy.
            if strategy_ins.is_param(strategy_ins, param_name) is False:
                dbg_warning(f'{param_name} is not a param of {strategy_ins.NAME}')
                strategy_ins.dump_params(strategy_ins)
                return False

            if args['#'] == 3:
                if '.' in args['3']:
                    self.bt_info.strategy_tune_param_grid[param_name] = [float(args['3'])]
                else:
                    self.bt_info.strategy_tune_param_grid[param_name] = [int(args['3'])]
            elif args['#'] == 4:
                if '.' in args['3']:
                    range_start = float(args['3'])
                    range_end = float(args['4'])
                    # default set to 0.5
                    range_step = float(0.5)
                    self.bt_info.strategy_tune_param_grid[param_name] = np.arange(range_start, range_end, range_step)
                else:
                    # get range.
                    range_start = int(args['3'])
                    range_end = int(args['4'])
                    # default set to 5
                    range_step = int(5)
                    self.bt_info.strategy_tune_param_grid[param_name] = range(range_start, range_end, range_step)
            elif args['#'] == 5:
                if '.' in args['3']:
                    range_start = float(args['3'])
                    range_end = float(args['4'])
                    range_step = float(args['5'])
                    self.bt_info.strategy_tune_param_grid[param_name] = np.arange(range_start, range_end, range_step)
                else:
                    # get range.
                    range_start = int(args['3'])
                    range_end = int(args['4'])
                    range_step = int(args['5'])
                    self.bt_info.strategy_tune_param_grid[param_name] = range(range_start, range_end, range_step)

            self.print(f"Current Paramte:{self.bt_info.strategy_tune_param_grid}")
            return True
        
        elif first_arg == 'del':
            if args['#'] < 2:
                self.print("Usage: strategy del [param name]")
                return False

            param_name = args['2']
            if param_name in self.bt_info.strategy_tune_param_grid.keys():
                self.bt_info.strategy_tune_param_grid.pop(param_name)
            self.print(f"Current Paramte:{self.bt_info.strategy_tune_param_grid}")
            return True

        elif first_arg == 'clean':

            self.bt_info.strategy_tune_param_grid = {}
            return True
        return False

    def cmd_mode(self, args):
        setting_list = self.total_mode_list
        if args['#'] == 1:
            if args['1'] in setting_list:
                self.bt_info.mode = args['1']
                self.print(f"mode          : {self.bt_info.mode}")
                return True
        return False
    def cmd_date(self, args):
        setting_list = self.set_date_list
        try:
            if args['#'] == 1:
                if args['1'].isdigit() and int(args['1']) < 100:
                    self.bt_info.to_date = datetime.today()
                    self.bt_info.from_date = datetime.today() - relativedelta(years=int(args['1']))
                elif args['1'] == 'd1':
                    self.bt_info.from_date = datetime.strptime('20000101', "%Y%m%d")
                    self.bt_info.to_date = self.bt_info.from_date + relativedelta(years=5) 
                elif args['1'] == 'd2':
                    self.bt_info.from_date = datetime.strptime('20050101', "%Y%m%d")
                    self.bt_info.to_date = self.bt_info.from_date + relativedelta(years=5) 
                elif args['1'] == 'd3':
                    self.bt_info.from_date = datetime.strptime('20100101', "%Y%m%d")
                    self.bt_info.to_date = self.bt_info.from_date + relativedelta(years=5) 
                elif args['1'] == 'd4':
                    self.bt_info.from_date = datetime.strptime('20150101', "%Y%m%d")
                    self.bt_info.to_date = self.bt_info.from_date + relativedelta(years=5) 
                elif args['1'] == 'd5':
                    self.bt_info.from_date = datetime.strptime('20200101', "%Y%m%d")
                    self.bt_info.to_date = self.bt_info.from_date + relativedelta(years=5)
            elif args['#'] == 2:
                if args['1'] == 'from':
                    if args['2'].isdigit() and int(args['2']) < 100:
                        self.bt_info.from_date = datetime.today() - relativedelta(years=int(args['2']))
                    else:
                        self.bt_info.from_date = datetime.strptime(args['2'], "%Y%m%d")
                elif args['1'] == 'to':
                    if args['2'].isdigit() and int(args['2']) < 100:
                        self.bt_info.to_date = datetime.today() - relativedelta(years=int(args['2']))
                    else:
                        self.bt_info.to_date = datetime.strptime(args['2'], "%Y%m%d")
                elif args['1'].startswith('y') and args['2'].isdigit():
                    year = int(args['2'])
                    self.bt_info.from_date = datetime(year, 1, 1)
                    self.bt_info.to_date = datetime(year, 12, 31)
            self.print(f"Set from date {self.bt_info.from_date}, to date {self.bt_info.to_date}.")
        except Exception as e:
            dbg_error(e)
            dbg_error("date should be like 20200101.")
            return False
        return True

    def cmd_report(self, args):
        setting_list = self.report_list

        results_display = BackResult(self.backtest.get_analysis())
        if args['#'] == 1 and args['1'] in setting_list:
            if args['1'] == 'result':
                results_display.show_analysis()
            elif args['1'] == 'annual':
                results_display.show_annual_return()
            elif args['1'] == 'average':
                results_display.show_analysis(mode = 'average')
                results_display.show_annual_return(mode = 'average')
            elif args['1'] == 'draw':
                self.backtest.show_drawing()
            elif args['1'] == 'save':
                # add more function of it.
                self.backtest.save_report()
            elif args['1'] == 'info':
                results_display.show_info()
            else:
                results_display.show_analysis()
        elif args['#'] == 2 and args['1'] in setting_list:
            if args['1'] == 'result':
                if args['2'] == 'average':
                    results_display.show_analysis(mode = 'average')
                else:
                    results_display.show_analysis()
            elif args['1'] == 'annual':
                if args['2'] == 'average':
                    results_display.show_annual_return(mode = 'average')
                else:
                    results_display.show_annual_return()
            else:
                if args['2'] == 'average':
                    results_display.show_analysis(mode = 'average')
                else:
                    results_display.show_analysis()
        else:
            results_display.show_analysis()
        return True

    def cmd_clean(self, args):
        self.backtest.clean_result()
        return True

    def cmd_evaluate(self, args):
        self.cmd_info()
        self.cmd_save_info({'#': 'eval_save', '1': self.def_autoinfo})

        try:
            self.backtest.clean_result()
            current_mode = self.bt_info.mode
            current_strategy_list = self.bt_info.strategy_list
            current_product_list = self.bt_info.product_list

            # preset 
            self.backtest.from_date = self.bt_info.from_date
            self.backtest.to_date = self.bt_info.to_date
            self.print(f"Date: {self.backtest.from_date} to {self.backtest.to_date}, {type(self.backtest.to_date)}")

            if current_mode == 'default':
                dbg_debug(f'Start evaluation.')
                for each_strategy in current_strategy_list:
                    target_strategy = self.strategyMgr.get_strategy_by_name(each_strategy)
                    for idx, each_product in enumerate(current_product_list):
                        dbg_info(f'[{target_strategy.NAME}][{idx + 1}/{len(current_product_list)}] Symbol: {each_product}', prefix='\r', end=' ' * 10)
                        self.backtest.setup(broker=self.broker)
                        self.backtest.add_symbol([each_product])
                        self.backtest.add_strategy([target_strategy])
                        self.backtest.eval()
                    dbg_info(f'[{target_strategy.NAME}] all {len(current_product_list)} products done', prefix='\n')
                self.backtest.show_result()
            elif current_mode == 'year':
                dbg_debug(f'Start yearly evaluation.')

                overall_from_date = self.bt_info.from_date
                overall_to_date = self.bt_info.to_date

                if not overall_from_date or not overall_to_date:
                    dbg_error("Please set 'from' and 'to' dates using the 'date' command before running yearly evaluation.")
                    return False

                # Store original dates to restore them after the yearly loop
                original_backtest_from_date = self.bt_info.from_date
                original_backtest_to_date = self.bt_info.to_date

                # New logic for monthly shifted yearly evaluation
                current_segment_start = overall_from_date
                
                while current_segment_start <= overall_to_date:
                    segment_end_date = current_segment_start + relativedelta(years=1) - relativedelta(days=1)

                    # Ensure the segment does not go beyond the overall_to_date
                    if segment_end_date > overall_to_date:
                        segment_end_date = overall_to_date
                    
                    # If the segment start date itself is beyond the overall_to_date, break
                    if current_segment_start > overall_to_date:
                        break

                    self.print(f"\n--- Evaluating for period: {current_segment_start.strftime('%Y-%m-%d')} to {segment_end_date.strftime('%Y-%m-%d')} ---")
                    
                    # Set backtest dates for the current yearly segment
                    # Add extra 6 months before test. feeds enough data for test.
                    self.backtest.from_date = current_segment_start - relativedelta(months=6)
                    self.backtest.to_date = segment_end_date

                    for each_strategy in current_strategy_list:
                        target_strategy = self.strategyMgr.get_strategy_by_name(each_strategy)
                        for idx, each_product in enumerate(current_product_list):
                            dbg_info(f'[{target_strategy.NAME}][{idx + 1}/{len(current_product_list)}] Symbol: {each_product}', prefix='\r', end=' ' * 10)
                            self.backtest.setup(broker=self.broker) # Setup for each product/strategy combination
                            self.backtest.add_symbol([each_product])
                            self.backtest.add_strategy([target_strategy])
                            self.backtest.eval()
                        dbg_info(f'[{target_strategy.NAME}] all {len(current_product_list)} products done for {current_segment_start.strftime("%Y-%m-%d")} to {segment_end_date.strftime("%Y-%m-%d")}', prefix='\n')
                    
                    # Move to the next segment (shift by one month)
                    current_segment_start += relativedelta(months=1)
                
                # Restore original dates after all yearly evaluations are complete
                self.bt_info.from_date = original_backtest_from_date
                self.bt_info.to_date = original_backtest_to_date

                self.backtest.show_result() # Show overall result after all yearly evaluations
            elif current_mode == 'opt':
                dbg_debug(f'Start opt evaluation.')
                # will be global
                if len(self.bt_info.strategy_tune_param_grid) == 0:
                    dbg_warning('No tuning params found.')
                    return False
                if len(current_strategy_list) > 1:
                    dbg_warning('Please keep only one strategy at a test time.')
                    return False
                for each_strategy in current_strategy_list:
                    target_strategy = self.strategyMgr.get_strategy_by_name(each_strategy)
                    for idx, each_product in enumerate(current_product_list):
                        dbg_info(f'[{target_strategy.NAME}][{idx + 1}/{len(current_product_list)}] Symbol: {each_product}', prefix='\r', end=' ' * 10)
                        self.backtest.setup(broker=self.broker)
                        self.backtest.add_symbol([each_product])
                        # self.backtest.add_strategy([target_strategy])
                        self.backtest.add_optstrategy(target_strategy, **self.bt_info.strategy_tune_param_grid)
                        self.backtest.eval(show_params = True)
                    dbg_info(f'[{target_strategy.NAME}] all {len(current_product_list)} products done', prefix='\n')
                self.backtest.show_result()

            # elif self.mode == 'single':
            #     # self.backtest.testSingle(strategy=self.strategy_list[0], product_list=self.product_list)
            #     for each_product in self.product_list:
            #         self.backtest.setup(broker=self.broker)
            #         self.backtest.add_symbol([each_product])
            #         self.backtest.add_strategy([self.strategyMgr.get_strategy_by_name(each_strategy) for each_strategy in self.strategy_list])
            #         self.backtest.eval()
            #     self.backtest.show_result()
            #
            # elif self.mode == 'mix':
            #     # self.backtest.testBatch(strategy_list = self.strategy_list, product_list = self.product_list)
            #     self.backtest.setup(broker=self.broker)
            #     self.backtest.add_symbol(self.product_list)
            #     self.backtest.add_strategy([self.strategyMgr.get_strategy_by_name(each_strategy) for each_strategy in self.strategy_list])
            #     self.backtest.eval()
            #
            #     self.backtest.show_result()
            else:
                dbg_error(f'Unknown test mode.{current_mode}')
                return False
        except Exception as e:
            dbg_error(e)

            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return False
        return True

    def cmd_save_info(self, args):
        file_path = ""
        if args['#'] != 1:
            self.print(f"Use default file.{self.def_autoinfo}")
            file_path = self.def_autoinfo
        else:
            # self.print("Usage: save_info [file_path]")
            # return False
            file_path = args['1']
        
        file_path = file_path + '.test'
        file_path = os.path.join(self.test_path, file_path)
        try:
            os.makedirs(self.test_path, exist_ok=True)
            info_dict = self.bt_info.to_dict()
            dbg_trace(f"Save info: {info_dict}")
            with open(file_path, 'w') as f:
                json.dump(info_dict, f, indent=4)
            self.print(f"Backtest info saved to {file_path}")
            return True
        except Exception as e:
            dbg_error(f"Failed to save backtest info: {e}")
            return False

    def cmd_load_info(self, args):
        file_path = ""
        if args['#'] != 1:
            self.print(f"Use default file.{self.def_autoinfo}")
            file_path = self.def_autoinfo
        else:
            file_path = args['1']

        file_path = file_path + '.test'
        file_path = os.path.join(self.test_path, file_path)
        try:
            with open(file_path, 'r') as f:
                info_dict = json.load(f)
            self.bt_info = BacktestInfo.from_dict(info_dict)
            # Update backtest dates as well, since bt_info is now new
            self.backtest.from_date = self.bt_info.from_date
            self.backtest.to_date = self.bt_info.to_date
            self.print(f"Backtest info loaded from {file_path}")
            self.cmd_info() # Show updated info
            return True
        except FileNotFoundError:
            dbg_error(f"File not found: {file_path}")
            return False
        except json.JSONDecodeError:
            dbg_error(f"Invalid JSON file: {file_path}")
            return False
        except Exception as e:
            dbg_error(f"Failed to load backtest info: {e}")
            return False
