# testutility/trading.py
import traceback
from datetime import date, timedelta

# Standard library
from unittest.mock import patch, MagicMock

# Local file
from trading.evaluate import Evaluate
from trading.trading import Trading # Import the Trading class
from utility.debug import dbg_info, dbg_warning, dbg_error, dbg_trace
from core.config import AppConfigManager # Evaluate uses this
from broker.order.constant import OrderAction
from broker.brokermanager import BrokerManager # Import BrokerManager for patching class methods

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"
# Define a default ticker for tests requiring one
DEFAULT_TEST_TICKER = '2330' # TSMC

# Mock Position class for testing selling_evaluation
class MockPosition:
    def __init__(self, symbol: str, size: float, open_date_iso: str, initial_entry_price: float):
        self.symbol = symbol
        self.size = size
        try:
            self.open_date = date.fromisoformat(open_date_iso)
        except ValueError:
            dbg_error(f"Invalid date format for MockPosition open_date: {open_date_iso}. Expected YYYY-MM-DD.")
            # Fallback or raise, depending on desired strictness. For tests, let's use today.
            self.open_date = date.today()
        self.initial_entry_price = initial_entry_price
        # The 'strategy' attribute is mentioned in Evaluate's test_sell_list,
        # but not strictly used by the Position object itself in Broker.
        # Adding it here for completeness if Evaluate's internal logic might expect it.
        self.strategy = "default_strategy"


def test_buying_evaluation() -> bool:
    """Tests the buying_evaluation method of Evaluate."""
    dbg_info("--- Running Test: Buying Evaluation ---")

    # Only patch the get_data_list method of the Market class
    with patch('trading.evaluate.Market.get_data_list') as mock_get_data_list:
        # Setup mock for Market.get_data_list()
        mock_get_data_list.return_value = ['2330', '2454'] # Define your test product list here

        evaluate_instance = Evaluate() # Create instance inside the test

        try:
            dbg_info("Calling evaluate_instance.buying_evaluation()...")
            result = evaluate_instance.buying_evaluation()
            if not isinstance(result, dict):
                dbg_error(f"buying_evaluation() did not return a dictionary. Got: {type(result)}")
                return False
            dbg_info(f"buying_evaluation() returned {len(result)} candidates: {list(result.keys())}")
            # Add more specific assertions based on expected behavior with test data if necessary
            return True
        except Exception as e:
            dbg_error(f"Error testing buying_evaluation: {e}")
            dbg_error(traceback.format_exc())
            return False


def test_selling_evaluation() -> bool:
    """Tests the selling_evaluation method of Evaluate."""
    dbg_info("--- Running Test: Selling Evaluation ---")
    BrokerManager.initialize(broker_type='mock', simulation=True) # Call the actual initialize (which is mocked)
    evaluate_instance = Evaluate() # Create instance inside the test

    # Create a mock position dictionary: {symbol: MockPosition_object}
    # Use dates that are likely to have data.
    # Ensure symbols exist in your test data or are handled gracefully by Market/Analyzer.
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    one_month_ago = (date.today() - timedelta(days=30)).isoformat()

    mock_positions = {
        "2330": MockPosition(symbol="2330", size=10, open_date_iso=one_month_ago, initial_entry_price=50.0),
        "2454": MockPosition(symbol="2454", size=5, open_date_iso=yesterday, initial_entry_price=100.0),
    }

    try:
        dbg_info(f"Calling evaluate_instance.selling_evaluation() with {len(mock_positions)} mock positions...")
        result = evaluate_instance.selling_evaluation(mock_positions)
        if not isinstance(result, list):
            dbg_error(f"selling_evaluation() did not return a list. Got: {type(result)}")
            return False
        dbg_info(f"selling_evaluation() returned {len(result)} sell candidates.")
        for item in result:
            if not isinstance(item, dict) or 'symbol' not in item:
                dbg_error(f"Invalid item in selling_evaluation result: {item}")
                return False
    except Exception as e:
            dbg_error(f"Error testing selling_evaluation: {e}")
            dbg_error(traceback.format_exc())
            return False
    finally:
        BrokerManager.finalize()
    return True

# --- Tests for Trading Class ---

def test_trading_buying_exec() -> bool:
    """Tests the buying_exec method of the Trading class."""
    dbg_info("--- Running Test: Trading buying_exec ---")
    all_passed = True
    BrokerManager.initialize(broker_type='mock', simulation=True)
    trading_instance = Trading() # Create instance inside the test
    try:
        with patch('trading.trading.AppConfigManager') as mock_app_config_manager_class, \
                patch('trading.trading.BrokerManager') as mock_broker_manager_class:

            dbg_info('inside', mock_broker_manager_class, mock_app_config_manager_class, trading_instance)
            # Setup AppConfigManager mock with values from core/config.py
            # These values are used by the Trading class internally via AppConfigManager.
            # For specific scenarios, we can override them within the test.
            default_lot_unit = 10
            default_cash_min_per_trade = 15000
            default_cash_max_per_trade = default_cash_min_per_trade * 2 # 30000

            mock_acm_instance = MagicMock()
            def acm_get_side_effect(key):
                if key == 'stock.lot_unit': return default_lot_unit
                if key == 'stock.cash_min_per_trade': return default_cash_min_per_trade
                if key == 'stock.cash_max_per_trade': return default_cash_max_per_trade
                return None
            mock_acm_instance.get.side_effect = acm_get_side_effect
            mock_app_config_manager_class.return_value = mock_acm_instance

            # Setup BrokerManager mock
            mock_broker_instance = MagicMock()
            mock_broker_manager_class.return_value = mock_broker_instance

            # Scenario 1: Empty buy_list
            dbg_info("Scenario 1: Empty buy_list")
            # For this scenario, no actual broker interaction is expected, so initialize/finalize are not called.
            trading_instance.buying_exec([])
            mock_broker_instance.connect.assert_not_called() # Trading should NOT call connect
            mock_broker_instance.disconnect.assert_not_called() # Trading should NOT call disconnect
            dbg_info("Scenario 1: Passed")

            # Scenario 2: Valid buy - sufficient funds, order placed
            dbg_info("Scenario 2: Valid buy")
            mock_broker_instance.reset_mock() # Reset for new scenario

            mock_broker_instance.get_balance.return_value = default_cash_max_per_trade * 2 # e.g., 60000
            mock_broker_instance.get_last_price.return_value = 10 # Price per unit
            buy_list_s2 = [DEFAULT_TEST_TICKER]
            dbg_info(trading_instance)
            trading_instance.buying_exec(buy_list_s2)
            mock_broker_instance.connect.assert_not_called() # Trading should NOT call connect
            # Expected calculation:
            # current_cash = 60000 * 0.9 = 54000
            # buying_budget = min(54000, 30000) = 30000
            # current_price = 10
            # order_lot = floor(30000 / (10 * 10)) = floor(30000 / 100) = 300
            # order_size = 300 * 10 = 3000
            # Check: 15000 <= (10 * 3000) <= 30000 -> 15000 <= 30000 <= 30000 (True)
            target_size = 3000
            mock_broker_instance.place_order.assert_called_with(symbol=DEFAULT_TEST_TICKER, size=target_size, action=OrderAction.BUY)
            mock_broker_instance.summarize_positions.assert_called_once()
            mock_broker_instance.disconnect.assert_not_called() # Trading should NOT call disconnect

            dbg_info("Scenario 2: Passed")

            # Scenario 3: Order lot becomes 0 (current_price * LOT_UNIT > buying_budget)
            dbg_info("Scenario 3: Order lot becomes 0")
            mock_broker_instance.reset_mock()

            mock_broker_instance.get_balance.return_value = default_cash_max_per_trade # e.g., 30000
            # Set price high enough so that order_lot becomes 0
            # current_cash = 30000 * 0.9 = 27000
            # buying_budget = min(27000, 30000) = 27000
            # To make order_lot = 0, current_price * LOT_UNIT > buying_budget
            # current_price * 10 > 27000 => current_price > 2700
            mock_broker_instance.get_last_price.return_value = 2701 # Makes order_lot = 0
            buy_list_s3 = [DEFAULT_TEST_TICKER]
            trading_instance.buying_exec(buy_list_s3)
            mock_broker_instance.connect.assert_not_called() # Trading should NOT call connect
            mock_broker_instance.place_order.assert_not_called() # No order should be placed
            mock_broker_instance.disconnect.assert_not_called() # Trading should NOT call disconnect

            dbg_info("Scenario 3: Passed")

            # Scenario 4: Calculated order value is less than CASH_MIN_PER_TRADE (but order_size > 0)
            dbg_info("Scenario 4: Calculated order value is less than CASH_MIN_PER_TRADE")
            mock_broker_instance.reset_mock()

            # Set config values for this scenario
            lot_unit_s4 = 10
            cash_max_per_trade_s4 = 150 # Max budget for this trade
            cash_min_per_trade_s4 = 500 # Minimum trade value
            mock_acm_instance.get.side_effect = lambda key: {
                'stock.lot_unit': lot_unit_s4,
                'stock.cash_max_per_trade': cash_max_per_trade_s4,
                'stock.cash_min_per_trade': cash_min_per_trade_s4,
            }.get(key)

            mock_broker_instance.get_balance.return_value = 200 # Enough cash for buying_budget
            mock_broker_instance.get_last_price.return_value = 10 # Price per unit
            buy_list_s4 = [DEFAULT_TEST_TICKER]
            trading_instance.buying_exec(buy_list_s4)
            mock_broker_instance.connect.assert_not_called() # Trading should NOT call connect
            # Expected:
            # current_cash = 200 * 0.9 = 180
            # buying_budget = min(180, 150) = 150
            # current_price = 10
            # order_lot = floor(150 / (10 * 10)) = floor(150 / 100) = 1
            # order_size = 1 * 10 = 10
            # current_price * order_size = 10 * 10 = 100
            # Since 100 < CASH_MIN_PER_TRADE (500), place_order should NOT be called.
            mock_broker_instance.place_order.assert_not_called()
            mock_broker_instance.summarize_positions.assert_called_once()
            mock_broker_instance.disconnect.assert_not_called()

            dbg_info("Scenario 4: Passed")

    except AssertionError as e:
        dbg_error(f"AssertionError in test_trading_buying_exec: {e}")
        dbg_error(traceback.format_exc())
        all_passed = False
    except Exception as e:
        dbg_error(f"Error in test_trading_buying_exec: {e}")
        dbg_error(traceback.format_exc())
        all_passed = False
    finally:
        BrokerManager.finalize()
    return all_passed

def test_trading_selling_exec() -> bool:
    """Tests the selling_exec method of the Trading class."""
    dbg_info("--- Running Test: Trading selling_exec ---")
    all_passed = True
    BrokerManager.initialize(broker_type='mock', simulation=True)
    trading_instance = Trading() # Create instance inside the test
    try:
        with patch('trading.trading.AppConfigManager') as mock_app_config_manager_class, \
                patch('trading.trading.BrokerManager') as mock_broker_manager_class:

            # Setup AppConfigManager mock
            cash_min_per_trade = 100 # Default for initial scenarios
            mock_acm_instance = MagicMock()
            def acm_get_side_effect(key):
                if key == 'stock.cash_min_per_trade': return cash_min_per_trade
                return None
            mock_acm_instance.get.side_effect = acm_get_side_effect
            mock_app_config_manager_class.return_value = mock_acm_instance

            mock_broker_instance = MagicMock()
            mock_broker_manager_class.return_value = mock_broker_instance

            # Scenario 1: Empty selling_list
            dbg_info("Scenario 1: Empty selling_list")
            trading_instance.selling_exec([])
            mock_broker_instance.connect.assert_not_called()
            mock_broker_instance.disconnect.assert_not_called()
            dbg_info("Scenario 1: Passed")

            # Scenario 2: Valid sell, size <= holding
            dbg_info("Scenario 2: Valid sell, size <= holding")
            mock_broker_instance.reset_mock()

            mock_position_s2 = MagicMock()
            mock_position_s2.size = 1000
            mock_broker_instance.get_position_by_symbol.return_value = mock_position_s2
            mock_broker_instance.get_last_price.return_value = 50 # Not strictly used by logic but good to mock
            selling_list_s2 = [{'symbol': DEFAULT_TEST_TICKER, 'size': 500, 'price': 50, 'strategy': 'test_strat'}]
            trading_instance.selling_exec(selling_list_s2)
            mock_broker_instance.connect.assert_not_called()
            mock_broker_instance.get_position_by_symbol.assert_called_with(DEFAULT_TEST_TICKER)
            mock_broker_instance.place_order.assert_called_with(symbol=DEFAULT_TEST_TICKER, size=500, action=OrderAction.SELL)
            mock_broker_instance.summarize_positions.assert_called_once()
            mock_broker_instance.disconnect.assert_not_called()

            dbg_info("Scenario 2: Passed")

            # Scenario 3: Valid sell, size > holding (sells holding size)
            dbg_info("Scenario 3: Valid sell, size > holding")
            mock_broker_instance.reset_mock()

            mock_position_s3 = MagicMock()
            mock_position_s3.size = 200
            mock_broker_instance.get_position_by_symbol.return_value = mock_position_s3
            selling_list_s3 = [{'symbol': DEFAULT_TEST_TICKER, 'size': 500, 'price': 50, 'strategy': 'test_strat'}]
            trading_instance.selling_exec(selling_list_s3)
            mock_broker_instance.connect.assert_not_called()
            mock_broker_instance.get_position_by_symbol.assert_called_with(DEFAULT_TEST_TICKER)
            mock_broker_instance.place_order.assert_called_with(symbol=DEFAULT_TEST_TICKER, size=200, action=OrderAction.SELL) # Should sell holding size
            mock_broker_instance.disconnect.assert_not_called()

            dbg_info("Scenario 3: Passed")

            # Scenario 4: Partial sell, but remaining/selling size value is less than CASH_MIN_PER_TRADE, so sell all.
            dbg_info("Scenario 4: Partial sell, but remaining/selling size value is less than CASH_MIN_PER_TRADE, so sell all.")
            mock_broker_instance.reset_mock()

            # Set config values for this scenario
            cash_min_per_trade_s4 = 500 # Minimum trade value
            mock_acm_instance.get.side_effect = lambda key: {
                'stock.cash_min_per_trade': cash_min_per_trade_s4,
            }.get(key)

            mock_position_s4 = MagicMock()
            mock_position_s4.size = 100 # Holding size
            mock_broker_instance.get_position_by_symbol.return_value = mock_position_s4
            mock_broker_instance.get_last_price.return_value = 10 # Price per unit

            # We want to sell 10 units.
            # holding_size = 100, selling_size = 10, current_price = 10
            # checking_size = min(10, 100 - 10) = min(10, 90) = 10
            # checking_size * current_price = 10 * 10 = 100
            # Since 100 < CASH_MIN_PER_TRADE (500), it should sell holding_size (100).
            selling_list_s4 = [{'symbol': DEFAULT_TEST_TICKER, 'size': 10, 'price': 10, 'strategy': 'test_strat'}]
            trading_instance.selling_exec(selling_list_s4)
            mock_broker_instance.connect.assert_not_called()
            mock_broker_instance.get_position_by_symbol.assert_called_with(DEFAULT_TEST_TICKER)
            mock_broker_instance.place_order.assert_called_with(symbol=DEFAULT_TEST_TICKER, size=100, action=OrderAction.SELL) # Should sell holding size
            mock_broker_instance.summarize_positions.assert_called_once()
            mock_broker_instance.disconnect.assert_not_called()

            dbg_info("Scenario 4: Passed")

            # Scenario 5: Partial sell, and remaining/selling size value is NOT less than CASH_MIN_PER_TRADE, so sell expected size.
            dbg_info("Scenario 5: Partial sell, and remaining/selling size value is NOT less than CASH_MIN_PER_TRADE, so sell expected size.")
            mock_broker_instance.reset_mock()

            # Set config values for this scenario
            cash_min_per_trade_s5 = 50 # Minimum trade value (lower than 100 from previous scenario)
            mock_acm_instance.get.side_effect = lambda key: {
                'stock.cash_min_per_trade': cash_min_per_trade_s5,
            }.get(key)

            mock_position_s5 = MagicMock()
            mock_position_s5.size = 100 # Holding size
            mock_broker_instance.get_position_by_symbol.return_value = mock_position_s5
            mock_broker_instance.get_last_price.return_value = 1000 # Price per unit

            # We want to sell 10 units.
            # holding_size = 100, selling_size = 10, current_price = 10
            # checking_size = min(10, 100 - 10) = min(10, 90) = 10
            # checking_size * current_price = 10 * 10 = 100
            # Since 100 IS NOT < CASH_MIN_PER_TRADE (50), it should sell selling_size (10).
            selling_list_s5 = [{'symbol': DEFAULT_TEST_TICKER, 'size': 20, 'price': 1000, 'strategy': 'test_strat'}]
            trading_instance.selling_exec(selling_list_s5)
            mock_broker_instance.connect.assert_not_called()
            mock_broker_instance.get_position_by_symbol.assert_called_with(DEFAULT_TEST_TICKER)
            mock_broker_instance.place_order.assert_called_with(symbol=DEFAULT_TEST_TICKER, size=20, action=OrderAction.SELL) # Should sell expected size
            mock_broker_instance.summarize_positions.assert_called_once()
            mock_broker_instance.disconnect.assert_not_called()

            dbg_info("Scenario 5: Passed")

    except AssertionError as e:
        dbg_error(f"AssertionError in test_trading_selling_exec: {e}")
        dbg_error(traceback.format_exc())
        all_passed = False
    except Exception as e:
        dbg_error(f"Error in test_trading_selling_exec: {e}")
        dbg_error(traceback.format_exc())
        all_passed = False
    finally:
        BrokerManager.finalize()
    return all_passed

def test_trading_trading_eval_flow() -> bool:
    """Tests the trading_eval method flow of the Trading class."""
    dbg_info("--- Running Test: Trading trading_eval_flow ---")
    BrokerManager.finalize()
    trading_instance = Trading() # Create instance inside the test
    try:
        # Patch Market.get_data_list to control the product list for evaluation
        with patch('trading.evaluate.Market.get_data_list') as mock_get_data_list, \
             patch('trading.evaluate.Market.get_data_info') as mock_get_data_info, \
             patch('trading.evaluate.Analyzer') as mock_analyzer_class, \
             patch('trading.evaluate.StrategyManager') as mock_strategy_manager_class:

            # Setup mock for Market.get_data_list()
            mock_get_data_list.return_value = [DEFAULT_TEST_TICKER]

            # Setup mock for Market.get_data_info() to provide product details
            mock_get_data_info.return_value = {
                'code': DEFAULT_TEST_TICKER,
                'type': '股票',
                'name': 'Mock Stock Name',
                'start': '2000-01-01',
                'market': 'listed',
                'category': 'Mock Category',
                'country': 'TW'
            }

            # Mock Analyzer and StrategyManager to control the evaluation logic
            mock_analyzer_instance = MagicMock()
            mock_analyzer_class.return_value = mock_analyzer_instance
            # Mock get_analysis to return a profitable result for the single ticker
            mock_analyzer_instance.get_analysis.return_value = [{'profit': 10, 'sharpe': 1, 'vwr': 1, 'drawdown': {'max':{'drawdown': 0}}, 'sqn': {'sqn': 1}, 'score': 5}]

            mock_strategy_instance = MagicMock()
            mock_strategy_manager_class.return_value = mock_strategy_instance
            # Mock get_default_strategy and get_strategy_by_name to return a mock strategy
            mock_strategy_instance.get_default_strategy.return_value = MagicMock(NAME="MockStrategy", last_trade={'action': 'buy', 'symbol': DEFAULT_TEST_TICKER, 'date': date.today(), 'price': 100, 'size': 10})
            mock_strategy_instance.get_strategy_by_name.return_value = MagicMock(NAME="MockStrategy", last_trade={'action': 'buy', 'symbol': DEFAULT_TEST_TICKER, 'date': date.today(), 'price': 100, 'size': 10})

            result = trading_instance.trading_eval()

            # Assert that Market.get_data_list was called by Evaluate
            mock_get_data_list.assert_called_once()

            # Assert that Analyzer and StrategyManager were used
            mock_analyzer_class.assert_called()
            mock_strategy_manager_class.assert_called_once()

            # Define the expected structure of the buying_dict returned by Evaluate.buying_evaluation
            # We expect DEFAULT_TEST_TICKER to be a key, and its value to be a dictionary with specific keys.
            if not isinstance(result, dict):
                dbg_error(f"trading_eval did not return a dictionary. Got: {type(result)}")
                return False
            
            if DEFAULT_TEST_TICKER not in result:
                dbg_error(f"Expected {DEFAULT_TEST_TICKER} in buying candidates, but not found.")
                return False
            
            # Check the structure of the returned dictionary for the default ticker
            candidate_data = result[DEFAULT_TEST_TICKER]
            if not isinstance(candidate_data, dict):
                dbg_error(f"Candidate data for {DEFAULT_TEST_TICKER} is not a dictionary. Got: {type(candidate_data)}")
                return False
            
            # Check for essential keys and their types based on the mocked Analyzer output
            expected_keys = ['strategy', 'profit', 'sharpe', 'vwr', 'drawdown', 'sqn', 'score']
            for key in expected_keys:
                if key not in candidate_data:
                    dbg_error(f"Missing key '{key}' in candidate data for {DEFAULT_TEST_TICKER}.")
                    return False
            
            # Assert specific values based on the mocked Analyzer output
            if candidate_data['score'] != 5:
                dbg_error(f"Expected score 5, got {candidate_data['score']}")
                return False

            dbg_info("Test Passed.")
            return True
    except AssertionError as e:
        dbg_error(f"AssertionError in test_trading_trading_eval_flow: {e}")
        return False
    except Exception as e:
        dbg_error(f"Error in test_trading_trading_eval_flow: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        BrokerManager.finalize()

def test_trading_selling_eval_flow() -> bool:
    """Tests the selling_eval method flow of the Trading class."""
    dbg_info("--- Running Test: Trading selling_eval_flow ---")
    # Simulate BrokerManager being initialized externally
    BrokerManager.initialize(broker_type='mock', simulation=True)
    try:
        with patch('trading.trading.Evaluate') as mock_evaluate_class, \
             patch('broker.brokermanager.BrokerManager.get_all_positions') as mock_broker_manager_get_all_positions:
            
            trading_instance = Trading() # Create instance inside the test
            
            # Create a realistic mock position using MockPosition class
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            mock_pos1 = MockPosition(symbol=DEFAULT_TEST_TICKER, size=10, open_date_iso=yesterday, initial_entry_price=100.0)
            mock_positions_dict = {DEFAULT_TEST_TICKER: mock_pos1}
            # Set the return value for the patched get_all_positions
            mock_broker_manager_get_all_positions.return_value = mock_positions_dict

            # Setup Evaluate mock
            mock_evaluate_instance = MagicMock()
            mock_evaluate_class.return_value = mock_evaluate_instance
            expected_sell_list = [{"symbol": DEFAULT_TEST_TICKER, "size": 5, "reason": "profit_target"}] # Example sell list
            mock_evaluate_instance.selling_evaluation.return_value = expected_sell_list

            result = trading_instance.selling_eval()

            mock_broker_manager_get_all_positions.assert_called_once() # Assert the patched method was called
            mock_evaluate_instance.selling_evaluation.assert_called_with(mock_positions_dict)

            if result != expected_sell_list:
                dbg_error(f"selling_eval did not return the expected sell list. Got: {result}, Expected: {expected_sell_list}")
                return False
            dbg_info("Test Passed.")
            return True
    except AssertionError as e:
        dbg_error(f"AssertionError in test_trading_selling_eval_flow: {e}")
        return False
    except Exception as e:
        dbg_error(f"Error in test_trading_selling_eval_flow: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        BrokerManager.finalize()

# --- Test Runner ---
def run_trading_tests(test_names: list[str]):
    """Runs specified trading tests for Evaluate and Trading classes."""
    results = {}
    # Test function and the type of instance it requires ('evaluate' or 'trading')
    all_tests_info = {
        "eval_buying": (test_buying_evaluation, 'evaluate'),
        "eval_selling": (test_selling_evaluation, 'evaluate'),
        "exec_buying": (test_trading_buying_exec, 'trading'),
        "exec_selling": (test_trading_selling_exec, 'trading'),
        "flow_trading_eval": (test_trading_trading_eval_flow, 'trading'),
        "flow_selling_eval": (test_trading_selling_eval_flow, 'trading'),
    }

    specified_tests_to_run = [name for name in test_names if name in all_tests_info] if "all" not in test_names else list(all_tests_info.keys())

    if not specified_tests_to_run:
        dbg_warning(f"No valid trading tests specified or found in: {test_names}")
        return {"total": 0, "passed": 0, "failed": 0}

    dbg_info(f"=== Starting Trading Tests ({', '.join(specified_tests_to_run)}) ===")
    total_passed = 0
    total_run = 0

    for name in specified_tests_to_run:
        test_func, _ = all_tests_info[name] # instance_type is no longer needed for passing
        total_run += 1
        dbg_trace(f"Executing test: {name}")
        try:
            # Test functions now create their own instances and handle mocks
            result = test_func()
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


    dbg_info(f"=== Trading Tests Summary ===")
    for name, result in results.items():
        if result == "SKIPPED":
            status_str = "SKIPPED"
        else:
            status_str = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        dbg_info(f"  {name:<30}: {status_str}")
    total_failed = total_run - total_passed
    passed_str = f"{GREEN}Passed: {total_passed}{RESET}"
    failed_str = f"{RED}Failed: {total_failed}{RESET}" if total_failed > 0 else f"Failed: {total_failed}"
    dbg_info(f"Total Tests Run: {total_run}, {passed_str}, {failed_str}")
    dbg_info("==========================")
    return {"total": total_run, "passed": total_passed, "failed": total_failed}


