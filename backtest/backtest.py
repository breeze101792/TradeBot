# system file
import traceback
import time

import backtrader as bt
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tabulate import tabulate # Import tabulate

# Local file
from utility.debug import *
from utility.utils import *
from core.database import *
from market.market import *
from backtest.backtest import *
from backtest.analyzer.partialtrade import *
from strategy.strategy import *

class Backtest:
    def __init__(self, market):
        # Internal storage for configuration attributes
        self._init_cash = 1000000000  # 10b to avoid buy fail.
        self._commission = 0.001
        self._slippage_prec = 0.001
        self._to_date = datetime.today() # Use property setter logic
        self._from_date = self.to_date - relativedelta(years=5) # Use property setter logic

        self.market = market
        self.default_strategy = MovingAverageCrossover
        self.default_product_list = self.market.get_top_product_list()

        self.cerebro = None
        self.data_list = []
        self.strategy_list = []
        self.result_list = []

        # every run cached.
        self.cached_validated_history = []

    # --- Property Getters/Setters for Configuration ---

    @property
    def init_cash(self):
        return self._init_cash

    @init_cash.setter
    def init_cash(self, value):
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError("Initial cash must be a positive number.")
        self._init_cash = value

    @property
    def commission(self):
        return self._commission

    @commission.setter
    def commission(self, value):
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError("Commission must be a non-negative number.")
        self._commission = value

    @property
    def slippage_prec(self):
        return self._slippage_prec

    @slippage_prec.setter
    def slippage_prec(self, value):
        if not isinstance(value, (int, float)) or value < 0:
            raise ValueError("Slippage percentage must be a non-negative number.")
        self._slippage_prec = value

    @property
    def to_date(self):
        return self._to_date

    @to_date.setter
    def to_date(self, value):
        if not isinstance(value, datetime):
            raise ValueError("to_date must be a datetime object.")
        # Optional: Add validation against from_date if needed
        # if hasattr(self, '_from_date') and self._from_date and value < self._from_date:
        #     raise ValueError("to_date cannot be earlier than from_date.")
        self._to_date = value

    @property
    def from_date(self):
        return self._from_date

    @from_date.setter
    def from_date(self, value):
        if not isinstance(value, datetime):
            raise ValueError("from_date must be a datetime object.")
        # Optional: Add validation against to_date if needed
        # if hasattr(self, '_to_date') and self._to_date and value > self._to_date:
        #     raise ValueError("from_date cannot be later than to_date.")
        self._from_date = value

    # --- End Properties ---

    def __setup_broker(self, cerebro = None):
        if cerebro is None:
            cerebro = self.cerebro

        # Setup init cash using internal attribute
        cerebro.broker.set_cash(self._init_cash)
        # Set commission using internal attribute
        cerebro.broker.setcommission(commission=self._commission)
        # set perc using internal attribute
        cerebro.broker.set_slippage_perc(perc=self._slippage_prec)
    def __setup_analyzer(self, cerebro = None):
        if cerebro is None:
            cerebro = self.cerebro
        # Add analyzer
        dbg_trace('Add analyzer.')
        cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name="annual_return")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", riskfreerate=0.02)
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.SQN, _name="sqn")
        cerebro.addanalyzer(bt.analyzers.VWR, _name="vwr")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trade_analyzer")

        # customize analyzer
        cerebro.addanalyzer(PartialTradeAnalyzer, _name="pta")
    def __analyze(self, strategy_list, cerebro = None):
        invalid_number = 101
        if cerebro is None:
            cerebro = self.cerebro
        # result_list = []

        for each_strategy in strategy_list:
            result_item = {}
            result_item['data'] = self.data_list
            result_item['strategy'] = [each_stra.NAME for each_stra in self.strategy_list]
            # Use internal attribute for reporting initial cash
            result_item['init_cash'] = self._init_cash
            result_item['cash'] = cerebro.broker.getvalue()

            # ann_returN
            result_item['annual_return'] = {}
            for year, ret in each_strategy.analyzers.annual_return.get_analysis().items():
                # print(f"{year}: {ret:.2%}, ")
                # ann_message += f"{year}: {ret:.2%}, "
                result_item['annual_return'][year] = ret * 100

            result_item['sharpe'] = each_strategy.analyzers.sharpe.get_analysis().get("sharperatio", invalid_number)
            result_item['vwr'] = each_strategy.analyzers.vwr.get_analysis().get("vwr", invalid_number)

            result_item['drawdown'] = each_strategy.analyzers.drawdown.get_analysis()
            result_item['sqn'] = each_strategy.analyzers.sqn.get_analysis()

            result_item['trade_analyzer'] = each_strategy.analyzers.trade_analyzer.get_analysis()

            # customize
            result_item['pta'] = each_strategy.analyzers.pta.get_analysis(summary = True)

            self.result_list.append(result_item)

    def setup(self, cerebro = None, broker = None):
        if cerebro is None:
            self.cerebro = bt.Cerebro()
        else:
            self.cerebro = cerebro
        self.data_list = []
        self.strategy_list = []
        if broker is not None:
            self.cerebro.setbroker(broker())
        else:
            self.__setup_broker()
        self.__setup_analyzer()

    def clean_result(self):
        self.result_list = []

    def get_analysis(self):
        if not self.result_list:
            return None
        else:
            return self.result_list

    def show_result(self, annual_return=False):
        """
        Displays the backtest results in a formatted table.
        """
        if not self.result_list:
            dbg_info("No results found to display.")
            return False

        headers = [
            "Symbol", "Strategy", "Profit %", "Sharpe", "VWR",
            "Max DD %", "SQN", "Buys", "Buy Win %", "Sells", "Sell Win %"
        ]
        table_data = []
        annual_returns_data = [] # Store annual returns separately for printing after table

        invalid_number = float('nan') # Use NaN for missing numeric data
        na_string = 'N/A' # String used by tabulate for missing values

        for i, each_result in enumerate(self.result_list):
            try:
                # --- Extract Data ---
                symbol_list = each_result.get('data', [])
                strategy_list = each_result.get('strategy', [])
                symbol = ",".join(map(str, symbol_list)) if symbol_list else na_string
                strategy = ",".join(map(str, strategy_list)) if strategy_list else na_string

                # Basic truncation (tabulate might handle wrapping better depending on format)
                symbol = (symbol[:27] + '...') if len(symbol) > 30 else symbol
                strategy = (strategy[:27] + '...') if len(strategy) > 30 else strategy


                init_cash = each_result.get('init_cash', 0)
                final_cash = each_result.get('cash', 0)
                profit_pct = ((final_cash / init_cash - 1) * 100) if init_cash != 0 else 0.0

                sharpe = each_result.get('sharpe', invalid_number)
                if sharpe is None or not isinstance(sharpe, (int, float)): sharpe = invalid_number

                vwr = each_result.get('vwr', invalid_number)
                if vwr is None or not isinstance(vwr, (int, float)): vwr = invalid_number

                drawdown = each_result.get('drawdown', {}).get('max', {}).get('drawdown', invalid_number)
                if drawdown is None or not isinstance(drawdown, (int, float)): drawdown = invalid_number

                sqn = each_result.get('sqn', {}).get('sqn', invalid_number)
                if sqn is None or not isinstance(sqn, (int, float)): sqn = invalid_number

                # Trade Analyzer (Buy side focus)
                trade_analyzer = each_result.get('trade_analyzer', {})
                buy_total = trade_analyzer.get('total', {}).get('total', 0)
                buy_won = trade_analyzer.get('won', {}).get('total', 0)
                buy_winning_rate = (buy_won / buy_total * 100) if buy_total > 0 else 0.0

                # Partial Trade Analyzer (Sell side focus - from pta)
                pta_analyzer = each_result.get('pta', {})
                sell_total = pta_analyzer.get('total_trades', 0)
                sell_won = pta_analyzer.get('won', 0)
                sell_winning_rate = (sell_won / sell_total * 100) if sell_total > 0 else 0.0

                annual_returns = each_result.get('annual_return', {})

                # --- Prepare Row Data for Tabulate ---
                row = [
                    symbol,
                    strategy,
                    profit_pct,
                    sharpe,
                    vwr,
                    drawdown, # Already a percentage
                    sqn,
                    buy_total,
                    buy_winning_rate,
                    sell_total,
                    sell_winning_rate
                ]
                table_data.append(row)

                # Store annual returns if requested
                if annual_return and annual_returns:
                    valid_returns = {str(year): ret for year, ret in annual_returns.items() if isinstance(ret, (int, float))}
                    if valid_returns:
                        annual_returns_data.append((strategy, valid_returns)) # Store with strategy name for context

            except Exception as e:
                dbg_error(f"Error processing result item index {i}: {e}")
                dbg_error(f"Problematic result item content: {each_result}")
                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                # Add an error row to the table data
                table_data.append([
                    'ERROR', f'Check Logs (Index {i})', None, None, None, None, None, None, None, None, None
                ])

        # --- Generate and Print Table ---
        try:
            # Use tabulate to create the table string
            # 'grid' format provides clear borders
            # 'floatfmt=".2f"' formats floats to 2 decimal places
            # 'stralign="right"' aligns strings to the right (like numbers)
            # 'missingval="N/A"' displays missing data as N/A
            table_str = tabulate(
                table_data,
                headers=headers,
                tablefmt="grid",
                floatfmt=".2f",
                stralign="right", # Align string columns right for consistency
                numalign="right", # Align numeric columns right
                missingval=na_string
            )
            print("\n--- Backtest Results Summary ---")
            print(table_str)

        except Exception as e:
            dbg_error(f"Error generating results table with tabulate: {e}")
            print("\nError: Could not generate results summary table.")

        # --- Print Annual Returns (Optional) ---
        if annual_return and annual_returns_data:
            print("\n--- Annual Returns ---")
            for strategy_name, returns in annual_returns_data:
                # Sort by year before printing
                annual_str = ", ".join([f"{year}: {ret:.2f}%" for year, ret in sorted(returns.items())])
                print(f"{strategy_name}: {annual_str}")
            print("-" * 20) # Separator

        print() # Add a blank line at the end
        return True # Indicate successful display attempt

    def add_data(self,product_list , cerebro = None):
        if cerebro is None:
            cerebro = self.cerebro

        for each_product in product_list:
            try:
                df = self.market.get_data(each_product)
                # Use internal attributes for date range
                data = bt.feeds.PandasData(dataname=df, fromdate=self._from_date, todate=self._to_date)

                dbg_trace(f"Add product {each_product}.")

                # Add data to enginee
                cerebro.adddata(data, name=each_product)

                self.data_list.append(each_product)
            except Exception as e:
                dbg_error("Error ticker: ", each_product)
                # self.update_tracking_list(each_product, False)
                dbg_error(e)

                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                continue

    def add_history(self, order_history, cerebro = None):
        if cerebro is None:
            cerebro = self.cerebro

        # --- Input Validation ---
        if not hasattr(order_history, '__iter__'):
            raise TypeError("Input 'order_history' must be an iterable (e.g., list or tuple).")

        self.cached_validated_history = []
        for i, order in enumerate(order_history):
            if not hasattr(order, '__len__') or len(order) != 4:
                raise ValueError(f"Order at index {i} is not a valid 4-element tuple/list: {order}")

            dt, size, price, data_name = order

            # Basic date check (not None or empty)
            if not dt:
                 raise ValueError(f"Order at index {i} has an invalid datetime: {dt}")
            # Could add more specific date checks if needed, e.g., isinstance(dt, (datetime, str))

            # Size check (non-zero integer)
            if not isinstance(size, int) or size == 0:
                raise ValueError(f"Order at index {i} has an invalid size (must be non-zero integer): {size}")

            # Price check (positive number)
            if not isinstance(price, (int, float)) or price <= 0:
                 raise ValueError(f"Order at index {i} has an invalid price (must be positive number): {price}")

            # Data name check (non-empty string)
            if not isinstance(data_name, str) or not data_name:
                 raise ValueError(f"Order at index {i} has an invalid data name (must be non-empty string): {data_name}")

            # Optional: Check if data_name exists in added data feeds
            # if data_name not in self.data_list:
            #     dbg_warning(f"Order at index {i} refers to data '{data_name}' which has not been added via add_data().")
            #     # Depending on requirements, you might raise ValueError here instead of just warning.

            self.cached_validated_history.append(order) # Add validated order

        # --- End Validation ---

        # must be sorted ascending (Backtrader expects this)
        # (datetime, size, price, data_name)
        # Example: order_history = (('2012-04-11', 10, 100.50, 'AAPL'), ('2012-05-01', -10, 105.20, 'AAPL'))
        dbg_trace(f"Adding {len(self.cached_validated_history)} validated historical orders.")
        # cerebro.add_order_history(self.cached_validated_history, notify = False)
        cerebro.add_order_history(self.cached_validated_history, notify = True)

    def add_strategy(self, strategy_list, cerebro = None):
        if cerebro is None:
            cerebro = self.cerebro

        for each_stra in strategy_list:
            dbg_trace(f"Add Straegy: {each_stra}")
            cerebro.addstrategy(each_stra)
            self.strategy_list.append(each_stra)

    def eval(self, cerebro = None):
        if len(self.cached_validated_history) != 0:
            # dbg_info('Set order history.')
            for each_stra in self.strategy_list:
                each_stra.initial_order_history = self.cached_validated_history
            self.cached_validated_history = []

        if cerebro is None:
            cerebro = self.cerebro
            stra_list = cerebro.run()
            self.__analyze(stra_list)

