# testutility/backtest.py
import os
import shutil
import traceback
from datetime import datetime, timedelta
import io
import contextlib
from unittest.mock import patch, MagicMock
import time # Added for eval_lock test

import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt # Import for mocking

# Local file
from utility.debug import dbg_info, dbg_warning, dbg_error, dbg_trace
from backtest.backtest import Backtest
from market.market import Market # We might need to mock this heavily

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

# Define test constants
TEST_REPORT_ROOT = "data/test_backtest_reports"
DEFAULT_BROKER_TEST_TICKER = '2330' # TSMC

# --- Mock Classes for Testing ---

class MockMarket:
    """A mock Market class for backtest data."""
    def get_data(self, product_name, start_date=None, end_date=None):
        """Generates simple dummy data for a given product."""
        # Ensure dates are datetime objects for consistency
        if start_date and not isinstance(start_date, datetime):
            start_date = datetime.combine(start_date, datetime.min.time())
        if end_date and not isinstance(end_date, datetime):
            end_date = datetime.combine(end_date, datetime.min.time())

        # Default date range if not provided
        if not start_date:
            start_date = datetime(2020, 1, 1)
        if not end_date:
            end_date = datetime(2020, 12, 31)

        # Generate dates within the requested range
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        if dates.empty:
            dbg_warning(f"No dates generated for {product_name} between {start_date} and {end_date}")
            return pd.DataFrame() # Return empty DataFrame if no dates

        num_periods = len(dates)
        data = {
            'open': [100 + i for i in range(num_periods)],
            'high': [101 + i for i in range(num_periods)],
            'low': [99 + i for i in range(num_periods)],
            'close': [100.5 + i for i in range(num_periods)],
            'volume': [1000 + i * 10 for i in range(num_periods)]
        }
        df = pd.DataFrame(data, index=dates)
        df.index.name = 'datetime'
        return df

    def get_top_product_list(self):
        return [DEFAULT_BROKER_TEST_TICKER, 'DUMMY_STOCK_B']

class MockStrategy(bt.Strategy):
    """A simple mock strategy for testing purposes."""
    NAME = "MockStrategy"
    params = (('p1', 1), ('p2', 2)) # Example params for optstrategy
    initial_order_history = [] # To check if history is passed

    def __init__(self):
        self.order = None
        self.dataclose = self.datas[0].close
        self.trading_date = None # To check if trading_date is passed

    def next(self):
        # Simulate some trading logic
        if not self.position:
            if self.dataclose[0] > 105:
                self.buy(size=1)
        elif self.dataclose[0] < 95:
            self.close()

    def get_name(self):
        return self.NAME

    def reset_status(self, *args, **kwargs):
        # Mock reset_status for testing eval
        pass

# --- Helper Functions ---

def _create_test_backtest_instance(test_name: str) -> Backtest:
    """Helper to create a Backtest instance with a unique report path for testing."""
    report_path = os.path.join(TEST_REPORT_ROOT, test_name)
    os.makedirs(report_path, exist_ok=True)
    
    mock_market = MockMarket()
    backtester = Backtest(mock_market)
    backtester.report_root_path = report_path # Override default report path
    
    # Set default dates for tests to ensure data is generated
    backtester.from_date = datetime(2020, 1, 1)
    backtester.to_date = datetime(2020, 12, 31)
    
    dbg_trace(f"Created Backtest instance for test '{test_name}' with report path: {report_path}")
    return backtester

def cleanup_test_backtest_files(test_name: str):
    """Cleans up files and directories created by a specific backtest."""
    report_path = os.path.join(TEST_REPORT_ROOT, test_name)
    if os.path.exists(report_path):
        try:
            shutil.rmtree(report_path)
            dbg_trace(f"Cleaned up report directory: {report_path}")
        except Exception as e:
            dbg_warning(f"Could not remove report directory {report_path}: {e}")

# --- Individual Test Functions ---

def test_initial_configuration(backtester: Backtest) -> bool:
    dbg_info("--- Running Test: Initial Configuration and Property Setters ---")
    try:
        # Test default values
        if backtester.init_cash != 1000000000:
            dbg_error(f"Default init_cash incorrect. Expected 1000000000, Got {backtester.init_cash}")
            return False
        if backtester.commission != 0.001:
            dbg_error(f"Default commission incorrect. Expected 0.001, Got {backtester.commission}")
            return False
        if backtester.slippage_prec != 0.001:
            dbg_error(f"Default slippage_prec incorrect. Expected 0.001, Got {backtester.slippage_prec}")
            return False
        
        # Test setters with valid values
        backtester.init_cash = 50000.0
        if backtester.init_cash != 50000.0:
            dbg_error(f"init_cash setter failed. Expected 50000.0, Got {backtester.init_cash}")
            return False
        
        backtester.commission = 0.005
        if backtester.commission != 0.005:
            dbg_error(f"commission setter failed. Expected 0.005, Got {backtester.commission}")
            return False

        backtester.slippage_prec = 0.0005
        if backtester.slippage_prec != 0.0005:
            dbg_error(f"slippage_prec setter failed. Expected 0.0005, Got {backtester.slippage_prec}")
            return False

        test_date = datetime(2023, 1, 1)
        backtester.from_date = test_date
        if backtester.from_date != test_date:
            dbg_error(f"from_date setter failed. Expected {test_date}, Got {backtester.from_date}")
            return False
        
        test_date_to = datetime(2023, 12, 31)
        backtester.to_date = test_date_to
        if backtester.to_date != test_date_to:
            dbg_error(f"to_date setter failed. Expected {test_date_to}, Got {backtester.to_date}")
            return False

        # Test setters with invalid values (should raise ValueError)
        try:
            backtester.init_cash = -100
            dbg_error("init_cash setter accepted negative value.")
            return False
        except ValueError:
            pass # Expected

        try:
            backtester.commission = -0.01
            dbg_error("commission setter accepted negative value.")
            return False
        except ValueError:
            pass # Expected

        try:
            backtester.slippage_prec = -0.01
            dbg_error("slippage_prec setter accepted negative value.")
            return False
        except ValueError:
            pass # Expected

        try:
            backtester.from_date = "not a date"
            dbg_error("from_date setter accepted invalid type.")
            return False
        except ValueError:
            pass # Expected

        dbg_info("Initial configuration and property setters OK.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_initial_configuration: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_setup_method(backtester: Backtest) -> bool:
    dbg_info("--- Running Test: setup() method ---")
    try:
        # Test default setup
        backtester.setup()
        if not isinstance(backtester.cerebro, bt.Cerebro):
            dbg_error("Cerebro not initialized correctly by setup().")
            return False
        if backtester.data_list: # Should be empty after setup
            dbg_warning("data_list is not empty after setup, which is unexpected.")
            return False
        if backtester.strategy_list: # Should be empty after setup
            dbg_warning("strategy_list is not empty after setup, which is unexpected.")
            return False
        
        # Test setup with custom cerebro (should not happen in normal use, but good for robustness)
        custom_cerebro = bt.Cerebro()
        backtester.setup(cerebro=custom_cerebro)
        if backtester.cerebro is not custom_cerebro:
            dbg_error("setup() did not use provided custom cerebro instance.")
            return False

        dbg_info("setup() method OK.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_setup_method: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_add_symbol(backtester: Backtest) -> bool:
    dbg_info("--- Running Test: add_symbol() ---")
    try:
        backtester.setup()
        # Mock cerebro.adddata to verify it's called
        with patch.object(backtester.cerebro, 'adddata') as mock_adddata:
            symbols = [DEFAULT_BROKER_TEST_TICKER, 'DUMMY_STOCK_B']
            backtester.add_symbol(symbols)
            
            if mock_adddata.call_count != len(symbols):
                dbg_error(f"adddata not called for all symbols. Expected {len(symbols)}, Got {mock_adddata.call_count}")
                return False
            
            if backtester.data_list != symbols:
                dbg_error(f"data_list not updated correctly. Expected {symbols}, Got {backtester.data_list}")
                return False
            
            # Verify arguments passed to adddata
            for i, symbol in enumerate(symbols):
                call_args, call_kwargs = mock_adddata.call_args_list[i]
                if call_kwargs.get('name') != symbol:
                    dbg_error(f"adddata called with incorrect name for symbol {symbol}.")
                    return False
                if not isinstance(call_args[0], bt.feeds.PandasData):
                    dbg_error(f"adddata called with incorrect data type for symbol {symbol}.")
                    return False

        dbg_info("add_symbol() OK.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_add_symbol: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_add_data_frame(backtester: Backtest) -> bool:
    dbg_info("--- Running Test: add_data_frame() ---")
    try:
        backtester.setup()
        # Create dummy DataFrames
        dates = pd.date_range(start='2020-01-01', periods=10, freq='D')
        df1 = pd.DataFrame({'open': range(10), 'high': range(10), 'low': range(10), 'close': range(10), 'volume': range(10)}, index=dates)
        df1.index.name = 'datetime'
        df2 = pd.DataFrame({'open': range(10), 'high': range(10), 'low': range(10), 'close': range(10), 'volume': range(10)}, index=dates)
        df2.index.name = 'datetime'

        symbol_data_list = [
            {'symbol': 'DF_STOCK_X', 'data': df1},
            {'symbol': 'DF_STOCK_Y', 'data': df2}
        ]

        with patch.object(backtester.cerebro, 'adddata') as mock_adddata:
            backtester.add_data_frame(symbol_data_list)
            
            if mock_adddata.call_count != len(symbol_data_list):
                dbg_error(f"adddata not called for all dataframes. Expected {len(symbol_data_list)}, Got {mock_adddata.call_count}")
                return False
            
            expected_data_list = ['DF_STOCK_X', 'DF_STOCK_Y']
            if backtester.data_list != expected_data_list:
                dbg_error(f"data_list not updated correctly. Expected {expected_data_list}, Got {backtester.data_list}")
                return False

        dbg_info("add_data_frame() OK.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_add_data_frame: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_add_history_validation(backtester: Backtest) -> bool:
    dbg_info("--- Running Test: add_history() Validation ---")
    try:
        backtester.setup()
        # Mock cerebro.add_order_history
        with patch.object(backtester.cerebro, 'add_order_history') as mock_add_order_history:
            # Test valid history
            valid_history = [
                (datetime(2021, 1, 1), 10, 100.0, DEFAULT_BROKER_TEST_TICKER),
                (datetime(2021, 1, 5), -5, 105.0, DEFAULT_BROKER_TEST_TICKER)
            ]
            backtester.add_history(valid_history)
            if not mock_add_order_history.called:
                dbg_error("add_order_history not called for valid input.")
                return False
            if backtester.cached_validated_history != valid_history:
                dbg_error("cached_validated_history not stored correctly.")
                return False
            mock_add_order_history.reset_mock() # Reset for next test

            # Test invalid history: not iterable
            try:
                backtester.add_history(None)
                dbg_error("add_history accepted non-iterable input.")
                return False
            except TypeError:
                pass # Expected

            # Test invalid history: wrong length tuple
            try:
                backtester.add_history([(datetime(2021, 1, 1), 10, 100.0)])
                dbg_error("add_history accepted wrong length tuple.")
                return False
            except ValueError:
                pass # Expected

            # Test invalid history: invalid size
            try:
                backtester.add_history([(datetime(2021, 1, 1), 0, 100.0, DEFAULT_BROKER_TEST_TICKER)])
                dbg_error("add_history accepted zero size.")
                return False
            except ValueError:
                pass # Expected
            try:
                backtester.add_history([(datetime(2021, 1, 1), "ten", 100.0, DEFAULT_BROKER_TEST_TICKER)])
                dbg_error("add_history accepted non-integer size.")
                return False
            except ValueError:
                pass # Expected

            # Test invalid history: invalid price
            try:
                backtester.add_history([(datetime(2021, 1, 1), 10, -100.0, DEFAULT_BROKER_TEST_TICKER)])
                dbg_error("add_history accepted negative price.")
                return False
            except ValueError:
                pass # Expected
            try:
                backtester.add_history([(datetime(2021, 1, 1), 10, "price", DEFAULT_BROKER_TEST_TICKER)])
                dbg_error("add_history accepted non-numeric price.")
                return False
            except ValueError:
                pass # Expected

            # Test invalid history: empty data_name
            try:
                backtester.add_history([(datetime(2021, 1, 1), 10, 100.0, '')])
                dbg_error("add_history accepted empty data_name.")
                return False
            except ValueError:
                pass # Expected

        dbg_info("add_history() validation OK.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_add_history_validation: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_add_strategy(backtester: Backtest) -> bool:
    dbg_info("--- Running Test: add_strategy() ---")
    try:
        backtester.setup()
        with patch.object(backtester.cerebro, 'addstrategy') as mock_addstrategy:
            strategies = [MockStrategy]
            test_trading_date = datetime(2022, 6, 15)
            backtester.add_strategy(strategies, last_trading_day=test_trading_date)
            
            if not mock_addstrategy.called:
                dbg_error("addstrategy not called.")
                return False
            if backtester.strategy_list != strategies:
                dbg_error(f"strategy_list not updated. Expected {strategies}, Got {backtester.strategy_list}")
                return False
            if backtester.cached_last_tradding_day != test_trading_date:
                dbg_error(f"cached_last_tradding_day not set. Expected {test_trading_date}, Got {backtester.cached_last_tradding_day}")
                return False

        dbg_info("add_strategy() OK.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_add_strategy: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_add_optstrategy(backtester: Backtest) -> bool:
    dbg_info("--- Running Test: add_optstrategy() ---")
    try:
        backtester.setup()
        with patch.object(backtester.cerebro, 'optstrategy') as mock_optstrategy:
            backtester.add_optstrategy(MockStrategy, p1=10, p2=20)
            
            if not mock_optstrategy.called:
                dbg_error("optstrategy not called.")
                return False
            
            call_args, call_kwargs = mock_optstrategy.call_args
            if call_args[0] != MockStrategy:
                dbg_error("optstrategy called with wrong strategy class.")
                return False
            if call_kwargs.get('p1') != 10 or call_kwargs.get('p2') != 20:
                dbg_error("optstrategy called with incorrect kwargs.")
                return False
            
            if backtester.strategy_list[0] != MockStrategy:
                dbg_error(f"strategy_list not updated. Expected [MockStrategy], Got {backtester.strategy_list}")
                return False

        dbg_info("add_optstrategy() OK.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_add_optstrategy: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_eval_basic(backtester: Backtest) -> bool:
    dbg_info("--- Running Test: eval() Basic Execution ---")
    try:
        backtester.setup()
        backtester.add_symbol([DEFAULT_BROKER_TEST_TICKER])
        backtester.add_strategy([MockStrategy])

        # Mock cerebro.run() to return a dummy strategy instance
        mock_strategy_instance = MagicMock()
        mock_strategy_instance.get_name.return_value = "MockStrategy"
        mock_strategy_instance.analyzers.annual_return.get_analysis.return_value = {2020: 0.1}
        mock_strategy_instance.analyzers.sharpe.get_analysis.return_value = {"sharperatio": 1.5}
        mock_strategy_instance.analyzers.vwr.get_analysis.return_value = {"vwr": 0.8}
        mock_strategy_instance.analyzers.drawdown.get_analysis.return_value = {'max': {'drawdown': 10.0}}
        mock_strategy_instance.analyzers.sqn.get_analysis.return_value = {'sqn': 2.0}
        mock_strategy_instance.analyzers.trade_analyzer.get_analysis.return_value = {'pnl': {'gross': {'total': 10000}}}
        mock_strategy_instance.analyzers.pta.get_analysis.return_value = {} # Mock custom analyzer
        mock_strategy_instance.reset_status.return_value = None # Mock reset_status

        with patch.object(backtester.cerebro, 'run', return_value=[mock_strategy_instance]) as mock_run, \
             patch.object(backtester.cerebro.broker, 'getvalue', return_value=backtester.init_cash + 10000): # Mock final cash
            
            backtester.eval(show_params = True)
            
            if not mock_run.called:
                dbg_error("cerebro.run() was not called.")
                return False
            
            analysis_results = backtester.get_analysis()
            if not analysis_results:
                dbg_error("No analysis results generated after eval.")
                return False
            
            if len(analysis_results) != 1:
                dbg_error(f"Expected 1 analysis result, got {len(analysis_results)}.")
                return False
            
            result = analysis_results[0]
            if result['strategy'] != ["MockStrategy"]:
                dbg_error(f"Strategy name in result incorrect. Got {result['strategy']}")
                return False
            if result['profit'] <= 0:
                dbg_error(f"Profit not calculated correctly. Got {result['profit']}")
                return False
            if result['score'] <= 0:
                dbg_error(f"Score not calculated correctly. Got {result['score']}")
                return False

        dbg_info("eval() basic execution OK.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_eval_basic: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_eval_with_history(backtester: Backtest) -> bool:
    dbg_info("--- Running Test: eval() with History ---")
    try:
        backtester.setup()
        backtester.add_symbol([DEFAULT_BROKER_TEST_TICKER])
        backtester.add_strategy([MockStrategy])
        
        test_history = [
            (datetime(2020, 1, 10), 10, 100.0, DEFAULT_BROKER_TEST_TICKER),
            (datetime(2020, 1, 20), -5, 105.0, DEFAULT_BROKER_TEST_TICKER)
        ]
        backtester.add_history(test_history)

        mock_strategy_instance = MagicMock()
        mock_strategy_instance.get_name.return_value = "MockStrategy"
        mock_strategy_instance.analyzers.annual_return.get_analysis.return_value = {2020: 0.1}
        mock_strategy_instance.analyzers.sharpe.get_analysis.return_value = {"sharperatio": 1.5}
        mock_strategy_instance.analyzers.vwr.get_analysis.return_value = {"vwr": 0.8}
        mock_strategy_instance.analyzers.drawdown.get_analysis.return_value = {'max': {'drawdown': 10.0}}
        mock_strategy_instance.analyzers.sqn.get_analysis.return_value = {'sqn': 2.0}
        mock_strategy_instance.analyzers.trade_analyzer.get_analysis.return_value = {'pnl': {'gross': {'total': 10000}}}
        mock_strategy_instance.analyzers.pta.get_analysis.return_value = {} # Mock custom analyzer
        mock_strategy_instance.reset_status.return_value = None # Mock reset_status

        with patch.object(backtester.cerebro, 'run', return_value=[mock_strategy_instance]) as mock_run, \
             patch.object(backtester.cerebro.broker, 'getvalue', return_value=backtester.init_cash + 10000):
            
            backtester.eval()
            
            # Verify that initial_order_history was set on the strategy instance
            # This requires inspecting the mock_strategy_instance after it's "run"
            # Since we return a mock, we can check its attributes directly.
            if MockStrategy.initial_order_history != test_history:
                dbg_error(f"Strategy's initial_order_history not set correctly. Expected {test_history}, Got {mock_strategy_instance.initial_order_history}")
                return False

        dbg_info("eval() with history OK.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_eval_with_history: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_save_report(backtester: Backtest, test_id="save_report_test") -> bool:
    dbg_info("--- Running Test: save_report() ---")
    try:
        # Ensure there are results to save
        backtester.setup()
        backtester.add_symbol([DEFAULT_BROKER_TEST_TICKER])
        backtester.add_strategy([MockStrategy])

        mock_strategy_instance = MagicMock()
        mock_strategy_instance.get_name.return_value = "MockStrategy"
        mock_strategy_instance.analyzers.annual_return.get_analysis.return_value = {2020: 0.1}
        mock_strategy_instance.analyzers.sharpe.get_analysis.return_value = {"sharperatio": 1.5}
        mock_strategy_instance.analyzers.vwr.get_analysis.return_value = {"vwr": 0.8}
        mock_strategy_instance.analyzers.drawdown.get_analysis.return_value = {'max': {'drawdown': 10.0}}
        mock_strategy_instance.analyzers.sqn.get_analysis.return_value = {'sqn': 2.0}
        mock_strategy_instance.analyzers.trade_analyzer.get_analysis.return_value = {'pnl': {'gross': {'total': 10000}}}
        mock_strategy_instance.analyzers.pta.get_analysis.return_value = {}
        mock_strategy_instance.reset_status.return_value = None

        # Mock the structure used in save_report: strat_fig[0].figure.savefig(...)
        mock_figure_obj = MagicMock()
        mock_figure_obj.savefig = MagicMock()  # <-- What will actually be called

        mock_fig_wrapper = MagicMock()
        mock_fig_wrapper.figure = mock_figure_obj

        with patch.object(backtester.cerebro, 'run', return_value=[mock_strategy_instance]), \
                patch.object(backtester.cerebro, 'plot', return_value=[[mock_fig_wrapper]]), \
                patch.object(backtester.cerebro.broker, 'getvalue', return_value=backtester.init_cash + 10000):

            backtester.eval()
            backtester.save_report()

            # Verify savefig was called
            if not mock_figure_obj.savefig.called:
                dbg_error("Figure.savefig was not called. Plot not saved.")
                return False
            
            # Check if the filename passed to savefig is correct
            # Example: bt_plot_MockStrategy.png
            expected_filename_part = "bt_plot_MockStrategy.png"
            called_with_filename = False
            for call_args, _ in mock_figure_obj.savefig.call_args_list:
                if expected_filename_part in call_args[0]:
                    called_with_filename = True
                    break
            if not called_with_filename:
                dbg_error(f"savefig not called with expected filename part '{expected_filename_part}'. Calls: {mock_savefig.call_args_list}")
                return False


        dbg_info("save_report() OK (files creation mocked/checked).")
        return True
    except Exception as e:
        dbg_error(f"Error in test_save_report: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_show_result(backtester: Backtest) -> bool:
    dbg_info("--- Running Test: show_result() ---")
    try:
        # Ensure there are results to show
        backtester.setup()
        backtester.add_symbol([DEFAULT_BROKER_TEST_TICKER])
        backtester.add_strategy([MockStrategy])

        mock_strategy_instance = MagicMock()
        mock_strategy_instance.get_name.return_value = "MockStrategy"
        mock_strategy_instance.analyzers.annual_return.get_analysis.return_value = {2020: 0.1}
        mock_strategy_instance.analyzers.sharpe.get_analysis.return_value = {"sharperatio": 1.5}
        mock_strategy_instance.analyzers.vwr.get_analysis.return_value = {"vwr": 0.8}
        mock_strategy_instance.analyzers.drawdown.get_analysis.return_value = {'max': {'drawdown': 10.0}}
        mock_strategy_instance.analyzers.sqn.get_analysis.return_value = {'sqn': 2.0}
        mock_strategy_instance.analyzers.trade_analyzer.get_analysis.return_value = {'pnl': {'gross': {'total': 10000}}}
        mock_strategy_instance.analyzers.pta.get_analysis.return_value = {}
        mock_strategy_instance.reset_status.return_value = None

        dbg_info('before with')
        output = ''
        with patch.object(backtester.cerebro, 'run', return_value=[mock_strategy_instance]), \
             patch.object(backtester.cerebro.broker, 'getvalue', return_value=backtester.init_cash + 10000), \
             patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            dbg_info('after with')
            
            backtester.eval(show_params=True) # Generate results
            backtester.show_result()
            
            output = mock_stdout.getvalue()
        # Check for expected strings in the output
        if "Backtest Results Summary" not in output:
            print(f"output:{output}")
            dbg_error("Expected 'Overall Analysis Summary' in show_result output.")
            return False
        if "MockStrategy" not in output:
            print(f"output:{output}")
            dbg_error("Expected 'MockStrategy' in show_result output.")
            return False
        if "Profit" not in output:
            print(f"output:{output}")
            dbg_error("Expected 'Profit' in show_result output.")
            return False

        dbg_info("show_result() OK (output checked).")
        return True
    except Exception as e:
        dbg_error(f"Error in test_show_result: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_eval_lock(backtester: Backtest) -> bool:
    dbg_info("--- Running Test: eval() Threading Lock Warning ---")
    try:
        # Mock the internal _EVAL_LOCK to control its behavior
        mock_lock = MagicMock()
        # Simulate that the lock is already held when eval is called
        mock_lock.locked.return_value = True 
        # Simulate acquire() and release() calls without actual blocking
        mock_lock.acquire.side_effect = lambda: dbg_trace("Mock lock acquire called.")
        mock_lock.release.side_effect = lambda: dbg_trace("Mock lock release called.")

        backtester.setup()
        with patch.object(backtester, '_EVAL_LOCK', new=mock_lock), \
             patch.object(backtester.cerebro, 'run') as mock_run:
            
            backtester.add_symbol([DEFAULT_BROKER_TEST_TICKER])
            backtester.add_strategy([MockStrategy])

            # Mock strategy instance for eval to return
            mock_strategy_instance = MagicMock()
            mock_strategy_instance.get_name.return_value = "MockStrategy"
            mock_strategy_instance.analyzers.annual_return.get_analysis.return_value = {2020: 0.1}
            mock_strategy_instance.analyzers.sharpe.get_analysis.return_value = {"sharperatio": 1.5}
            mock_strategy_instance.analyzers.vwr.get_analysis.return_value = {"vwr": 0.8}
            mock_strategy_instance.analyzers.drawdown.get_analysis.return_value = {'max': {'drawdown': 10.0}}
            mock_strategy_instance.analyzers.sqn.get_analysis.return_value = {'sqn': 2.0}
            mock_strategy_instance.analyzers.trade_analyzer.get_analysis.return_value = {'pnl': {'gross': {'total': 10000}}}
            mock_strategy_instance.analyzers.pta.get_analysis.return_value = {}
            mock_strategy_instance.reset_status.return_value = None

            mock_run.return_value = [mock_strategy_instance]
            
            backtester.eval()
            
            # Check if the mock lock's acquire method was called
            if not mock_lock.acquire.called:
                dbg_error("Mock lock's acquire method was not called.")
                return False
            
            # Check if the mock lock's release method was called (should be in finally block of eval)
            if not mock_lock.release.called:
                dbg_error("Mock lock's release method was not called.")
                return False
            
            # Check if cerebro.run was called (it should proceed after "acquiring" the mock lock)
            if not mock_run.called:
                dbg_error("cerebro.run() was not called.")
                return False

        dbg_info("eval() threading lock warning mechanism OK.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_eval_lock: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        # Ensure the real lock is released if it was acquired by the test setup
        # (This is a safeguard, should not be necessary if mock is used correctly)
        if backtester._EVAL_LOCK.locked():
            backtester._EVAL_LOCK.release()

# --- Test Runner ---

def run_backtest_tests(test_names: list[str]):
    results = {}
    
    # Map test names to functions
    all_test_definitions = {
        "initial_configuration": test_initial_configuration,
        "setup_method": test_setup_method,
        "add_symbol": test_add_symbol,
        "add_data_frame": test_add_data_frame,
        "add_history_validation": test_add_history_validation,
        "add_strategy": test_add_strategy,
        "add_optstrategy": test_add_optstrategy,
        "eval_basic": test_eval_basic,
        "eval_with_history": test_eval_with_history,
        "save_report": test_save_report,
        "show_result": test_show_result,
        "eval_lock": test_eval_lock,
    }

    tests_to_run_names = []
    if "all" in test_names:
        tests_to_run_names = list(all_test_definitions.keys())
    else:
        tests_to_run_names = [name for name in test_names if name in all_test_definitions]

    if not tests_to_run_names:
        dbg_warning(f"No valid backtest tests specified or found in: {test_names}")
        return {"total": 0, "passed": 0, "failed": 0}

    dbg_info("=== Starting Backtest Tests ===")
    total_passed = 0
    
    # Clean up root test directory before running tests
    if os.path.exists(TEST_REPORT_ROOT):
        shutil.rmtree(TEST_REPORT_ROOT)
        dbg_trace(f"Cleaned up root test directory: {TEST_REPORT_ROOT}")
    os.makedirs(TEST_REPORT_ROOT, exist_ok=True)

    for name in tests_to_run_names:
        dbg_trace(f"Executing test: {name}")
        backtester_instance = None # Initialize outside try for finally block
        try:
            # Create a fresh Backtest instance for each test for isolation
            backtester_instance = _create_test_backtest_instance(name)
            test_func = all_test_definitions[name]
            result = test_func(backtester_instance)
            
            results[name] = result
            if result:
                total_passed += 1
            status_str = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
            dbg_info(f"--- Test Result [{name}]: {status_str} ---")
        except Exception as e:
            dbg_error(f"!!! Exception during test [{name}]: {e} !!!")
            dbg_error(traceback.format_exc())
            results[name] = False
        finally:
            # Clean up files for this specific test
            cleanup_test_backtest_files(name)
        dbg_info("-" * 40)

    # Final cleanup of the root test directory if empty
    try:
        if os.path.exists(TEST_REPORT_ROOT) and not os.listdir(TEST_REPORT_ROOT):
            shutil.rmtree(TEST_REPORT_ROOT)
            dbg_trace(f"Cleaned up empty root test directory: {TEST_REPORT_ROOT}")
        data_dir = "data"
        if os.path.exists(data_dir) and not os.listdir(data_dir):
            shutil.rmtree(data_dir)
            dbg_trace(f"Cleaned up empty directory: {data_dir}")
    except OSError as e:
        dbg_warning(f"Warning during final cleanup of test directories: {e}")

    dbg_info("=== Backtest Tests Summary ===")
    for name, result in results.items():
        status_str = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        dbg_info(f"  {name:<30}: {status_str}")
    total_failed = len(tests_to_run_names) - total_passed
    passed_str = f"{GREEN}Passed: {total_passed}{RESET}"
    failed_str = f"{RED}Failed: {total_failed}{RESET}" if total_failed > 0 else f"Failed: {total_failed}"
    dbg_info(f"Total Tests Run: {len(tests_to_run_names)}, {passed_str}, {failed_str}")
    dbg_info("==========================")
    return {"total": len(tests_to_run_names), "passed": total_passed, "failed": total_failed}

# Example usage (for direct execution of this file, not part of the main CLI)
if __name__ == "__main__":
    # This block is for local testing of this test file itself.
    # It won't be part of the final solution for the user, but helps in development.
    # To run all tests:
    run_backtest_tests(["all"])
    # To run specific tests:
    # run_backtest_tests(["test_initial_configuration", "test_add_symbol"])

