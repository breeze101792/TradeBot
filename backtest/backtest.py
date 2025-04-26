# system file
import traceback
import time

import backtrader as bt
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Local file
from utility.debug import *
from utility.utils import *
from core.database import *
from market.market import *
from backtest.backtest import *
from backtest.analyzer.partialtrade import *
from strategy.strategy import *

class Backtest:
    INIT_CASH = 1000000
    COMMISSION = 0.001
    SLIPPAGE_PREC = 0.001
    TO_DATE=datetime.today()
    FROM_DATE=TO_DATE - relativedelta(years=5)

    def __init__(self, market):
        self.market = market
        self.default_strategy = MovingAverageCrossover
        self.default_product_list = self.market.get_top_product_list()

        self.cerebro = None
        self.data_list = []
        self.strategy_list = []
        self.result_list = []

        # every run cached.
        self.cached_validated_history = []

    def __setup_broker(self, cerebro = None):
        if cerebro is None:
            cerebro = self.cerebro

        # Setup init cash
        cerebro.broker.set_cash(self.INIT_CASH)
        # Set commission
        cerebro.broker.setcommission(commission=self.COMMISSION)
        # set perc
        cerebro.broker.set_slippage_perc(perc=self.SLIPPAGE_PREC)
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
            result_item['init_cash'] = self.INIT_CASH
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

        # Define column widths
        col_widths = {
            "symbol": 10,
            "strategy": 15,
            "profit_pct": 10,
            "sharpe": 8,
            "vwr": 8,
            "max_dd": 8,
            "sqn": 8,
            "buys": 6,
            "buy_win_pct": 10, # e.g., "   95.00%"
            "sells": 6,
            "sell_win_pct": 10, # e.g., "   95.00%"
        }

        # Create header string using defined widths
        header = (
            f"{'Symbol':<{col_widths['symbol']}} | "
            f"{'Strategy':<{col_widths['strategy']}} | "
            f"{'Profit %':>{col_widths['profit_pct']}} | "
            f"{'Sharpe':>{col_widths['sharpe']}} | "
            f"{'VWR':>{col_widths['vwr']}} | "
            f"{'Max DD %':>{col_widths['max_dd']}} | "
            f"{'SQN':>{col_widths['sqn']}} | "
            f"{'Buys':>{col_widths['buys']}} | "
            f"{'Buy Win %':>{col_widths['buy_win_pct']}} | "
            f"{'Sells':>{col_widths['sells']}} | "
            f"{'Sell Win %':>{col_widths['sell_win_pct']}}"
        )
        separator = "-" * len(header)

        print("\n" + separator)
        print(header)
        print(separator)

        invalid_number = float('nan') # Use NaN for missing numeric data
        na_string = 'N/A'

        for i, each_result in enumerate(self.result_list):
            # dbg_trace(f"Processing result item {i}: {each_result}")
            try:
                # --- Extract Data ---
                symbol_list = each_result.get('data', [na_string])
                strategy_list = each_result.get('strategy', [na_string])
                symbol = ",".join(map(str, symbol_list)) # Ensure elements are strings
                strategy = ",".join(map(str, strategy_list))

                # Truncate if too long for the column
                if len(symbol) > col_widths['symbol']:
                    symbol = symbol[:col_widths['symbol']-3] + "..."
                if len(strategy) > col_widths['strategy']:
                    strategy = strategy[:col_widths['strategy']-3] + "..."

                init_cash = each_result.get('init_cash', 0)
                final_cash = each_result.get('cash', 0)
                profit_pct = ((final_cash / init_cash - 1) * 100) if init_cash != 0 else 0.0

                sharpe = each_result.get('sharpe', invalid_number)
                # Handle cases where Sharpe might be None or non-numeric before formatting
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

                # --- Format Data ---
                profit_pct_str = f"{profit_pct:>{col_widths['profit_pct']}.2f}"
                sharpe_str = f"{sharpe:>{col_widths['sharpe']}.2f}" if not pd.isna(sharpe) else f"{na_string:>{col_widths['sharpe']}}"
                vwr_str = f"{vwr:>{col_widths['vwr']}.2f}" if not pd.isna(vwr) else f"{na_string:>{col_widths['vwr']}}"
                # Drawdown is already a percentage, format it
                drawdown_str = f"{drawdown:>{col_widths['max_dd']}.2f}" if not pd.isna(drawdown) else f"{na_string:>{col_widths['max_dd']}}"
                sqn_str = f"{sqn:>{col_widths['sqn']}.2f}" if not pd.isna(sqn) else f"{na_string:>{col_widths['sqn']}}"

                buy_cnt_str = f"{buy_total:>{col_widths['buys']}}"
                buy_win_pct_str = f"{buy_winning_rate:>{col_widths['buy_win_pct']}.2f}"
                sell_cnt_str = f"{sell_total:>{col_widths['sells']}}"
                sell_win_pct_str = f"{sell_winning_rate:>{col_widths['sell_win_pct']}.2f}"

                # --- Print Row ---
                data_row = (
                    f"{symbol:<{col_widths['symbol']}} | "
                    f"{strategy:<{col_widths['strategy']}} | "
                    f"{profit_pct_str} | "
                    f"{sharpe_str} | "
                    f"{vwr_str} | "
                    f"{drawdown_str} | "
                    f"{sqn_str} | "
                    f"{buy_cnt_str} | "
                    f"{buy_win_pct_str} | "
                    f"{sell_cnt_str} | "
                    f"{sell_win_pct_str}"
                )
                print(data_row)

                # --- Print Annual Returns (Optional) ---
                if annual_return and annual_returns:
                    # Ensure keys are strings/ints and values are numeric for sorting and formatting
                    valid_returns = {str(year): ret for year, ret in annual_returns.items() if isinstance(ret, (int, float))}
                    if valid_returns:
                        # Sort by year before printing
                        annual_str = ", ".join([f"{year}: {ret:.2f}%" for year, ret in sorted(valid_returns.items())])
                        # Indent nicely under the strategy column
                        indent = col_widths['symbol'] + 3 # Width of symbol column + " | "
                        print(f"{' ' * indent}{'Annual Returns:':<15} {annual_str}")

            except Exception as e:
                dbg_error(f"Error processing result item index {i}: {e}")
                # Print the item causing issues for easier debugging
                dbg_error(f"Problematic result item content: {each_result}")
                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
                # Print an error row in the table
                error_row = (
                    f"{'ERROR':<{col_widths['symbol']}} | "
                    f"{'Check Logs':<{col_widths['strategy']}} | "
                    + " | ".join([f"{'-':>{col_widths[k]}}" for k in list(col_widths.keys())[2:]]) # Fill remaining columns with '-'
                )
                print(error_row)

        print(separator + "\n") # Footer separator
        return True # Indicate successful display attempt

    def add_data(self,product_list , cerebro = None):
        if cerebro is None:
            cerebro = self.cerebro

        for each_product in product_list:
            try:
                df = self.market.get_data(each_product)
                data = bt.feeds.PandasData(dataname=df, fromdate=self.FROM_DATE, todate=self.TO_DATE)

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
        cerebro.add_order_history(self.cached_validated_history, notify = False)

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

