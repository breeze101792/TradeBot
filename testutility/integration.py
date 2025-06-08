# testutility/integration.py
import traceback
from unittest.mock import patch, MagicMock
from datetime import date, datetime, timedelta
import pandas as pd

from utility.debug import dbg_info, dbg_warning, dbg_error, dbg_trace
from trading.trading import Trading
from broker.brokermanager import BrokerManager
from market.market import Market, MarketTime
from core.config import AppConfigManager
from strategy.strategy import StrategyManager
from backtest.backtest import Backtest
from broker.order.constant import OrderAction

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

# Mock classes/data for testing
class MockPosition:
    def __init__(self, symbol, size, open_date, initial_entry_price):
        self.symbol = symbol
        self.size = size
        self.open_date = open_date
        self.initial_entry_price = initial_entry_price

# --- Integration Test Definitions ---
def test_buying_flow(test_id: str) -> bool:
    dbg_info(f"--- Running Test: Buying Flow ({test_id}) ---")
    try:
        # Mock all external dependencies and internal components that interact with external systems
        with patch('broker.brokermanager.BrokerManager') as MockBrokerManager, \
             patch('market.market.Market') as MockMarket, \
             patch('trading.evaluate.Market') as MockEvaluateMarket, \
             patch('trading.evaluate.BrokerManager') as MockEvaluateBrokerManager, \
             patch('trading.evaluate.AppConfigManager') as MockEvaluateAppConfigManager, \
             patch('trading.trading.BrokerManager') as MockTradingBrokerManager, \
             patch('trading.trading.AppConfigManager') as MockTradingAppConfigManager, \
             patch('market.market.MarketTime') as MockMarketTime, \
             patch('trading.evaluate.MarketTime') as MockEvaluateMarketTime, \
             patch('trading.evaluate.datetime') as MockEvaluateDatetime, \
             patch('strategy.strategy.StrategyManager') as MockStrategyManagerEval, \
             patch('trading.evaluate.StrategyManager') as MockStrategyManagerTrading, \
             patch('trading.evaluate.Analyzer') as MockBacktest:

            # Configure Mock AppConfigManager
            mock_cfg_mgr = MagicMock(spec=AppConfigManager)
            mock_cfg_mgr.get.side_effect = lambda key: {
                'debug.development': False, # Disable development mode to use mocked market.get_data_list
                'stock.lot_unit': 1000,
                'stock.cash_max_per_trade': 1000000,
                'stock.cash_min_per_trade': 1000
            }.get(key, None)
            MockEvaluateAppConfigManager.return_value = mock_cfg_mgr
            MockTradingAppConfigManager.return_value = mock_cfg_mgr

            # Configure Mock MarketTime
            test_date = datetime(2024, 6, 7, 10, 0, 0) # A fixed date for deterministic tests
            MockMarketTime.get_previous_market_update_time.return_value = test_date
            MockEvaluateMarketTime.get_previous_market_update_time.return_value = test_date
            MockEvaluateMarketTime.get_next_market_open_time.return_value = test_date + timedelta(days=1)
            MockEvaluateMarketTime.get_next_market_close_time.return_value = test_date + timedelta(hours=4)
            MockEvaluateMarketTime.is_trading_day.return_value = True
            MockEvaluateDatetime.now.return_value = test_date
            MockEvaluateDatetime.date.return_value = test_date.date() # For date.today() if used

            # Configure Mock Market
            mock_market = MagicMock(spec=Market)
            mock_market.get_data_list.return_value = ['2330', '0050'] # Example products
            mock_market.get_data_info.side_effect = lambda symbol: {
                '2330': {'code': '2330', 'name': 'TSMC', 'type': 'Stock', 'market': 'TWSE', 'category': 'Semiconductor', 'start': '1994-09-05', 'country': 'TW'},
                '0050': {'code': '0050', 'name': 'Taiwan 50', 'type': 'ETF', 'market': 'TWSE', 'category': 'ETF', 'start': '2003-10-24', 'country': 'TW'}
            }.get(symbol)
            mock_df_index = pd.to_datetime(pd.date_range(end=test_date, periods=365, freq='D'))
            mock_market.get_data.return_value = pd.DataFrame({
                'Open': [100 + i for i in range(365)],
                'High': [105 + i for i in range(365)],
                'Low': [99 + i for i in range(365)],
                'Close': [102 + i for i in range(365)],
                'Volume': [1000 + i*10 for i in range(365)],
                'Turnover': [100000 + i*100 for i in range(365)] # Added Turnover
            }, index=mock_df_index)

            MockMarket.return_value = mock_market
            MockEvaluateMarket.return_value = mock_market

            # Configure Mock BrokerManager
            mock_broker = MagicMock(spec=BrokerManager)
            mock_broker.get_balance.return_value = 10000000 # Mock balance
            mock_broker.get_last_price.side_effect = lambda symbol: {'2330': 600, '0050': 150}.get(symbol, 0)
            mock_broker.place_order.return_value = True # Mock order placement success
            mock_broker.summarize_positions.return_value = None
            mock_broker.connect.return_value = True
            mock_broker.disconnect.return_value = True
            mock_broker.get_all_positions.return_value = {} # No positions initially for buying test
            mock_broker.get_position_by_symbol.return_value = None

            MockBrokerManager.return_value = mock_broker
            MockEvaluateBrokerManager.return_value = mock_broker
            MockTradingBrokerManager.return_value = mock_broker


            # Configure Mock StrategyManager
            mock_strategy_manager_instance = MagicMock(spec=StrategyManager)
            mock_strategy = MagicMock()
            mock_strategy.NAME = "MockStrategy"
            # Simulate a buy signal from the strategy's last_trade
            mock_strategy.last_trade = {'action': 'buy', 'symbol': '2330', 'date': test_date.date(), 'price': 600, 'size': 1000}
            mock_strategy_manager_instance.get_default_strategy.return_value = mock_strategy
            mock_strategy_manager_instance.get_strategy_by_name.return_value = mock_strategy
            MockStrategyManagerEval.return_value = mock_strategy_manager_instance
            MockStrategyManagerTrading.return_value = mock_strategy_manager_instance

            # Configure Mock Backtest (Analyzer)
            mock_backtest_instance = MagicMock()
            mock_backtest_instance.clean_result.return_value = None
            mock_backtest_instance.setup.return_value = None
            mock_backtest_instance.add_symbol.return_value = None
            mock_backtest_instance.add_data_frame.return_value = None
            mock_backtest_instance.add_strategy.return_value = None
            mock_backtest_instance.eval.return_value = None
            # For buying flow, we need eval() to return a report with a score
            mock_backtest_instance.get_analysis.return_value = [{'profit': 10, 'sharpe': 1.5, 'vwr': 2.0, 'drawdown': {'max': {'drawdown': 5}}, 'sqn': {'sqn': 2.5}, 'score': 5.0}]
            MockBacktest.return_value = mock_backtest_instance

            # Instantiate Trading after mocks are set up
            trading_instance = Trading()

            # 1. Run buying evaluation
            dbg_info("Running buying evaluation...")
            buy_list = trading_instance.trading_eval()
            dbg_info(f"Buying evaluation returned: {buy_list.keys()}")

            if '2330' not in buy_list:
                dbg_error("Expected '2330' to be a buying candidate but it was not.")
                return False

            # 2. Execute buying orders
            dbg_info("Executing buying orders...")
            trading_instance.buying_exec(buy_list)

            # Assertions:
            mock_broker.place_order.assert_called_with(symbol='2330', size=1000, action=OrderAction.BUY)
            dbg_info(f"BrokerManager.place_order was called {mock_broker.place_order.call_count} times.")

            dbg_info("Buying flow test passed.")
            return True
    except Exception as e:
        dbg_error(f"Error in test_buying_flow: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_selling_flow(test_id: str) -> bool:
    dbg_info(f"--- Running Test: Selling Flow ({test_id}) ---")
    try:
        # Mock all external dependencies and internal components that interact with external systems
        with patch('broker.brokermanager.BrokerManager') as MockBrokerManager, \
             patch('market.market.Market') as MockMarket, \
             patch('trading.evaluate.Market') as MockEvaluateMarket, \
             patch('trading.evaluate.BrokerManager') as MockEvaluateBrokerManager, \
             patch('trading.evaluate.AppConfigManager') as MockEvaluateAppConfigManager, \
             patch('trading.trading.BrokerManager') as MockTradingBrokerManager, \
             patch('trading.trading.AppConfigManager') as MockTradingAppConfigManager, \
             patch('market.market.MarketTime') as MockMarketTime, \
             patch('trading.evaluate.MarketTime') as MockEvaluateMarketTime, \
             patch('trading.evaluate.datetime') as MockEvaluateDatetime, \
             patch('strategy.strategy.StrategyManager') as MockStrategyManagerEval, \
             patch('trading.evaluate.StrategyManager') as MockStrategyManagerTrading, \
             patch('backtest.backtest.Backtest') as MockBacktest:

            # patch('trading.trading.StrategyManager') as MockStrategyManagerTrading, \
            # Configure Mock AppConfigManager
            mock_cfg_mgr = MagicMock(spec=AppConfigManager)
            mock_cfg_mgr.get.side_effect = lambda key: {
                'debug.development': False, # Disable development mode to use mocked market.get_data_list
                'stock.lot_unit': 1000,
                'stock.cash_max_per_trade': 100000,
                'stock.cash_min_per_trade': 1000
            }.get(key, None)
            MockEvaluateAppConfigManager.return_value = mock_cfg_mgr
            MockTradingAppConfigManager.return_value = mock_cfg_mgr

            # Configure Mock MarketTime
            test_date = datetime(2024, 6, 7, 10, 0, 0) # A fixed date for deterministic tests
            MockMarketTime.get_previous_market_update_time.return_value = test_date
            MockEvaluateMarketTime.get_previous_market_update_time.return_value = test_date
            MockEvaluateMarketTime.get_next_market_open_time.return_value = test_date + timedelta(days=1)
            MockEvaluateMarketTime.get_next_market_close_time.return_value = test_date + timedelta(hours=4)
            MockEvaluateMarketTime.is_trading_day.return_value = True
            MockEvaluateDatetime.now.return_value = test_date
            MockEvaluateDatetime.date.return_value = test_date.date()

            # Configure Mock Market
            mock_market = MagicMock(spec=Market)
            mock_market.get_data_list.return_value = ['2330', '0050'] # Example products
            mock_market.get_data_info.side_effect = lambda symbol: {
                '2330': {'code': '2330', 'name': 'TSMC', 'type': 'Stock', 'market': 'TWSE', 'category': 'Semiconductor', 'start': '1994-09-05', 'country': 'TW'},
                '0050': {'code': '0050', 'name': 'Taiwan 50', 'type': 'ETF', 'market': 'TWSE', 'category': 'ETF', 'start': '2003-10-24', 'country': 'TW'}
            }.get(symbol)
            mock_df_index = pd.to_datetime(pd.date_range(end=test_date, periods=365, freq='D'))
            mock_market.get_data.return_value = pd.DataFrame({
                'Open': [100 + i for i in range(365)],
                'High': [105 + i for i in range(365)],
                'Low': [99 + i for i in range(365)],
                'Close': [102 + i for i in range(365)],
                'Volume': [1000 + i*10 for i in range(365)],
                'Turnover': [100000 + i*100 for i in range(365)] # Added Turnover
            }, index=mock_df_index)

            MockMarket.return_value = mock_market
            MockEvaluateMarket.return_value = mock_market

            # Configure Mock BrokerManager
            mock_broker = MagicMock(spec=BrokerManager)
            mock_broker.get_balance.return_value = 1000000 # Mock balance
            mock_broker.get_last_price.side_effect = lambda symbol: {'2330': 600, '0050': 150}.get(symbol, 0)
            mock_broker.place_order.return_value = True # Mock order placement success
            mock_broker.summarize_positions.return_value = None
            mock_broker.connect.return_value = True
            mock_broker.disconnect.return_value = True

            # Set up mock positions for selling evaluation
            mock_positions = {
                '2330': MockPosition('2330', 5000, date(2023, 1, 1), 550), # Position that might generate a sell signal
                '0050': MockPosition('0050', 2000, date(2023, 3, 15), 140)
            }
            mock_broker.get_all_positions.return_value = mock_positions
            mock_broker.get_position_by_symbol.side_effect = lambda symbol: mock_positions.get(symbol)

            MockBrokerManager.return_value = mock_broker
            MockEvaluateBrokerManager.return_value = mock_broker
            MockTradingBrokerManager.return_value = mock_broker

            # Configure Mock StrategyManager
            mock_strategy_manager_instance = MagicMock(spec=StrategyManager)
            mock_strategy = MagicMock()
            mock_strategy.NAME = "MockStrategy"
            # Simulate a sell signal from the strategy's last_trade for '2330'
            mock_strategy.last_trade = {'action': 'sell', 'symbol': '2330', 'date': test_date.date(), 'price': 600, 'size': 5000}
            mock_strategy_manager_instance.get_default_strategy.return_value = mock_strategy
            mock_strategy_manager_instance.get_strategy_by_name.return_value = mock_strategy
            MockStrategyManagerEval.return_value = mock_strategy_manager_instance
            MockStrategyManagerTrading.return_value = mock_strategy_manager_instance

            # Configure Mock Backtest (Analyzer)
            mock_backtest_instance = MagicMock()
            mock_backtest_instance.clean_result.return_value = None
            mock_backtest_instance.setup.return_value = None
            mock_backtest_instance.add_symbol.return_value = None
            mock_backtest_instance.add_data_frame.return_value = None
            mock_backtest_instance.add_strategy.return_value = None
            mock_backtest_instance.eval.return_value = None
            # For selling flow, get_analysis is not directly used to determine sell signal,
            # but it's called. Provide a dummy return.
            mock_backtest_instance.get_analysis.return_value = [{'profit': -10, 'sharpe': -0.5, 'vwr': -1.0, 'drawdown': {'max': {'drawdown': 10}}, 'sqn': {'sqn': -0.5}, 'score': -1.0}]
            MockBacktest.return_value = mock_backtest_instance

            # Instantiate Trading after mocks are set up
            trading_instance = Trading()

            # 1. Run selling evaluation
            dbg_info("Running selling evaluation...")
            sell_list = trading_instance.selling_eval()
            dbg_info(f"Selling evaluation returned: {sell_list}")

            if not any(item['symbol'] == '2330' for item in sell_list):
                dbg_error("Expected '2330' to be a selling candidate but it was not.")
                return False

            # 2. Execute selling orders
            dbg_info("Executing selling orders...")
            trading_instance.selling_exec(sell_list)

            # Assertions:
            mock_broker.place_order.assert_called_with(symbol='2330', size=5000, action=OrderAction.SELL)
            dbg_info(f"BrokerManager.place_order was called {mock_broker.place_order.call_count} times.")

            dbg_info("Selling flow test passed.")
            return True
    except Exception as e:
        dbg_error(f"Error in test_selling_flow: {e}")
        dbg_error(traceback.format_exc())
        return False

# --- Test Runner ---
def run_integration_tests(test_names: list[str]):
    results = {}
    
    # All integration test definitions
    all_test_definitions = {
        "buying_flow": test_buying_flow,
        "selling_flow": test_selling_flow,
    }

    tests_to_run_names = []
    if "all" in test_names:
        tests_to_run_names = list(all_test_definitions.keys())
    else:
        tests_to_run_names = [name for name in test_names if name in all_test_definitions]

    if not tests_to_run_names:
        dbg_warning(f"No valid integration tests specified or found in: {test_names}")
        return {"total": 0, "passed": 0, "failed": 0}

    dbg_info("=== Starting Integration Tests ===")
    total_passed = 0
    for name in tests_to_run_names:
        dbg_trace(f"Executing test: {name}")
        try:
            test_id = f"{name}_cli" # Create a unique test ID for each standalone test
            test_func = all_test_definitions[name]
            result = test_func(test_id) # All test functions now accept test_id
            
            results[name] = result
            if result:
                total_passed += 1
            status_str = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
            dbg_info(f"--- Test Result [{name}]: {status_str} ---")
        except Exception as e:
            dbg_error(f"!!! Exception during test [{name}]: {e} !!!")
            dbg_error(traceback.format_exc())
            results[name] = False
        dbg_info("-" * 40)

    dbg_info("=== Integration Tests Summary ===")
    for name, result in results.items():
        status_str = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        dbg_info(f"  {name:<30}: {status_str}")
    total_failed = len(tests_to_run_names) - total_passed
    passed_str = f"{GREEN}Passed: {total_passed}{RESET}"
    failed_str = f"{RED}Failed: {total_failed}{RESET}" if total_failed > 0 else f"Failed: {total_failed}"
    dbg_info(f"Total Tests Run: {len(tests_to_run_names)}, {passed_str}, {failed_str}")
    dbg_info("==========================")
    return {"total": len(tests_to_run_names), "passed": total_passed, "failed": total_failed}

