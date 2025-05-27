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


def test_buying_evaluation(evaluate_instance: Evaluate) -> bool:
    """Tests the buying_evaluation method of Evaluate."""
    dbg_info("--- Running Test: Buying Evaluation ---")
    # Ensure flag_development is True to use test lists if defined in Evaluate
    # and to potentially speed up the process by limiting product lists.
    original_flag_development = evaluate_instance.flag_development
    evaluate_instance.flag_development = True
    # Ensure test_buy_list is populated if Evaluate relies on it for dev mode
    if not evaluate_instance.test_buy_list: # Default is ['2028', '8404']
        dbg_warning("evaluate_instance.test_buy_list is empty. Using default test buy list for testing.")
        evaluate_instance.test_buy_list = ['2028', '8404']


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
    finally:
        evaluate_instance.flag_development = original_flag_development

def test_selling_evaluation(evaluate_instance: Evaluate) -> bool:
    """Tests the selling_evaluation method of Evaluate."""
    dbg_info("--- Running Test: Selling Evaluation ---")
    original_flag_development = evaluate_instance.flag_development
    original_test_sell_list = evaluate_instance.test_sell_list

    evaluate_instance.flag_development = True
    # Critical: To prevent evaluate.py's internal self.test_sell_list (list of dicts)
    # from being assigned to position_dict and causing .items() error,
    # we clear it. The test will provide a correctly structured dict of MockPosition objects.
    evaluate_instance.test_sell_list = []


    # Create a mock position dictionary: {symbol: MockPosition_object}
    # Use dates that are likely to have data.
    # Ensure symbols exist in your test data or are handled gracefully by Market/Analyzer.
    # Using symbols that might be in evaluate_instance.test_buy_list for consistency.
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    one_month_ago = (date.today() - timedelta(days=30)).isoformat()

    mock_positions = {
        "2028": MockPosition(symbol="2028", size=10, open_date_iso=one_month_ago, initial_entry_price=50.0),
        "8404": MockPosition(symbol="8404", size=5, open_date_iso=yesterday, initial_entry_price=100.0),
    }
    # If evaluate_instance.test_sell_list was used, it would be:
    # [{'symbol':'2330', 'open_date':date.today().isoformat(), 'size':5, 'initial_entry_price':2000, 'strategy': 'DefaultStrategyName'}]
    # This is a list of dicts, not a dict of Position objects, which is why we clear it.

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
        return True
    except Exception as e:
        dbg_error(f"Error testing selling_evaluation: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        evaluate_instance.flag_development = original_flag_development
        evaluate_instance.test_sell_list = original_test_sell_list

# --- Tests for Trading Class ---

@patch('trading.trading.AppConfigManager')
@patch('trading.trading.BrokerManager')
def test_trading_buying_exec(trading_instance: Trading, mock_broker_manager_class: MagicMock, mock_app_config_manager_class: MagicMock) -> bool:
    """Tests the buying_exec method of the Trading class."""
    dbg_info("--- Running Test: Trading buying_exec ---")
    dbg_info('inside', mock_broker_manager_class, mock_app_config_manager_class,trading_instance)
    all_passed = True
    try:
        # Setup AppConfigManager mock
        mock_acm_instance = MagicMock()
        def acm_get_side_effect(key):
            if key == 'stock.lot_unit': return 1000
            if key == 'stock.cash_per_trade': return 50000
            return None
        mock_acm_instance.get.side_effect = acm_get_side_effect
        mock_app_config_manager_class.return_value = mock_acm_instance

        # Setup BrokerManager mock
        mock_broker_instance = MagicMock()
        mock_broker_manager_class.return_value = mock_broker_instance

        # Scenario 1: Empty buy_list
        dbg_info("Scenario 1: Empty buy_list")
        trading_instance.buying_exec([])
        mock_broker_instance.connect.assert_not_called() # Should not connect if list is empty
        dbg_info("Scenario 1: Passed")

        # Scenario 2: Valid buy
        dbg_info("Scenario 2: Valid buy")
        mock_broker_instance.reset_mock() # Reset for new scenario
        mock_broker_instance.get_cash.return_value = 100000
        mock_broker_instance.get_last_price.return_value = 60 # Results in order_lot = 1, order_size = 1000
        buy_list_s2 = [DEFAULT_TEST_TICKER]
        dbg_info(trading_instance)
        trading_instance.buying_exec(buy_list_s2)
        mock_broker_instance.connect.assert_called_once()
        mock_broker_instance.place_order.assert_called_with(symbol=DEFAULT_TEST_TICKER, size=1000, action='buy')
        mock_broker_instance.summarize_positions.assert_called_once()
        mock_broker_instance.disconnect.assert_called_once()
        dbg_info("Scenario 2: Passed")

        # Scenario 3: Insufficient cash for calculated order (price * order_size >= buying_budget after order_size calc)
        # This specific internal check `if current_price * order_size < buying_budget:`
        # with order_size = floor(budget / (price * lot_unit)) * lot_unit
        # means order_size * price will always be <= budget / lot_unit * lot_unit.
        # The warning `Insufficient cash (buget {buying_budget}), ignore buying product` seems hard to hit with current logic
        # unless get_cash() * 0.9 is very small or CASH_PER_TRADE is very small.
        # Let's test the "order_lot becomes 0" case.
        dbg_info("Scenario 3: Order lot becomes 0")
        mock_broker_instance.reset_mock()
        mock_broker_instance.get_cash.return_value = 50000
        mock_broker_instance.get_last_price.return_value = 60 # budget=50k, price*lot=60k -> order_lot=0
        buy_list_s3 = [DEFAULT_TEST_TICKER]
        trading_instance.buying_exec(buy_list_s3)
        mock_broker_instance.connect.assert_called_once()
        # place_order would be called with size 0 if order_lot is 0 due to `if current_price * order_size < buying_budget` (0 < 50000)
        mock_broker_instance.place_order.assert_called_with(symbol=DEFAULT_TEST_TICKER, size=0, action='buy')
        dbg_info("Scenario 3: Passed")

    except AssertionError as e:
        dbg_error(f"AssertionError in test_trading_buying_exec: {e}")
        dbg_error(traceback.format_exc())
        all_passed = False
    except Exception as e:
        dbg_error(f"Error in test_trading_buying_exec: {e}")
        dbg_error(traceback.format_exc())
        all_passed = False
    return all_passed

@patch('trading.trading.BrokerManager')
def test_trading_selling_exec(trading_instance: Trading, mock_broker_manager_class: MagicMock) -> bool:
    """Tests the selling_exec method of the Trading class."""
    dbg_info("--- Running Test: Trading selling_exec ---")
    all_passed = True
    try:
        mock_broker_instance = MagicMock()
        mock_broker_manager_class.return_value = mock_broker_instance

        # Scenario 1: Empty selling_list
        dbg_info("Scenario 1: Empty selling_list")
        trading_instance.selling_exec([])
        mock_broker_instance.connect.assert_not_called()
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
        mock_broker_instance.connect.assert_called_once()
        mock_broker_instance.get_position_by_symbol.assert_called_with(DEFAULT_TEST_TICKER)
        mock_broker_instance.place_order.assert_called_with(symbol=DEFAULT_TEST_TICKER, size=500, action='sell')
        mock_broker_instance.summarize_positions.assert_called_once()
        mock_broker_instance.disconnect.assert_called_once()
        dbg_info("Scenario 2: Passed")

        # Scenario 3: Valid sell, size > holding (sells holding size)
        dbg_info("Scenario 3: Valid sell, size > holding")
        mock_broker_instance.reset_mock()
        mock_position_s3 = MagicMock()
        mock_position_s3.size = 200
        mock_broker_instance.get_position_by_symbol.return_value = mock_position_s3
        selling_list_s3 = [{'symbol': DEFAULT_TEST_TICKER, 'size': 500, 'price': 50, 'strategy': 'test_strat'}]
        trading_instance.selling_exec(selling_list_s3)
        mock_broker_instance.connect.assert_called_once()
        mock_broker_instance.get_position_by_symbol.assert_called_with(DEFAULT_TEST_TICKER)
        mock_broker_instance.place_order.assert_called_with(symbol=DEFAULT_TEST_TICKER, size=200, action='sell') # Should sell holding size
        dbg_info("Scenario 3: Passed")

    except AssertionError as e:
        dbg_error(f"AssertionError in test_trading_selling_exec: {e}")
        dbg_error(traceback.format_exc())
        all_passed = False
    except Exception as e:
        dbg_error(f"Error in test_trading_selling_exec: {e}")
        dbg_error(traceback.format_exc())
        all_passed = False
    return all_passed

@patch('trading.trading.Evaluate')
def test_trading_trading_eval_flow(trading_instance: Trading, mock_evaluate_class: MagicMock) -> bool:
    """Tests the trading_eval method flow of the Trading class."""
    dbg_info("--- Running Test: Trading trading_eval_flow ---")
    try:
        mock_evaluate_instance = MagicMock()
        mock_evaluate_class.return_value = mock_evaluate_instance
        expected_buy_list = [{"symbol": DEFAULT_TEST_TICKER, "price": 100}] # Example buy list
        mock_evaluate_instance.buying_evaluation.return_value = expected_buy_list

        # NOTE: The current trading_eval does not call __buying_exec.
        # If it did, and depended on AppConfigManager for a debug flag:
        # @patch('trading.trading.AppConfigManager')
        # def test_with_acm(mock_acm_class, mock_evaluate_class, trading_instance):
        #   mock_acm_instance = MagicMock()
        #   mock_acm_instance.get.return_value = True # for 'debug.development'
        #   mock_acm_class.return_value = mock_acm_instance
        #   with patch.object(trading_instance, '_Trading__buying_exec', MagicMock()) as mock_private_buying_exec:
        #       result = trading_instance.trading_eval()
        #       mock_private_buying_exec.assert_called_with(expected_buy_list)

        result = trading_instance.trading_eval()
        mock_evaluate_instance.buying_evaluation.assert_called_once()
        if result != expected_buy_list:
            dbg_error(f"trading_eval did not return the expected buy list. Got: {result}, Expected: {expected_buy_list}")
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

@patch('trading.trading.BrokerManager')
@patch('trading.trading.Evaluate')
def test_trading_selling_eval_flow(trading_instance: Trading, mock_evaluate_class: MagicMock, mock_broker_manager_class: MagicMock) -> bool:
    """Tests the selling_eval method flow of the Trading class."""
    dbg_info("--- Running Test: Trading selling_eval_flow ---")
    try:
        # Setup BrokerManager mock
        mock_broker_instance = MagicMock()
        mock_broker_manager_class.return_value = mock_broker_instance
        mock_pos1 = MagicMock()
        mock_pos1.symbol = DEFAULT_TEST_TICKER; mock_pos1.size = 10
        mock_positions_dict = {DEFAULT_TEST_TICKER: mock_pos1}
        mock_broker_instance.get_all_positions.return_value = mock_positions_dict

        # Setup Evaluate mock
        mock_evaluate_instance = MagicMock()
        mock_evaluate_class.return_value = mock_evaluate_instance
        expected_sell_list = [{"symbol": DEFAULT_TEST_TICKER, "size": 5, "reason": "profit_target"}] # Example sell list
        mock_evaluate_instance.selling_evaluation.return_value = expected_sell_list

        result = trading_instance.selling_eval()

        mock_broker_instance.connect.assert_called_once()
        mock_broker_instance.get_all_positions.assert_called_once()
        mock_evaluate_instance.selling_evaluation.assert_called_with(mock_positions_dict)
        mock_broker_instance.disconnect.assert_called_once()

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

# --- Test Runner ---
def run_trading_tests(test_names: list[str], evaluate_instance: Evaluate = None, trading_instance: Trading = None):
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

    specified_tests_to_run = []
    if "all" in test_names:
        # If "all" is requested, try to run all defined tests for which instances are provided
        for name, (_, instance_type) in all_tests_info.items():
            if instance_type == 'evaluate' and evaluate_instance:
                specified_tests_to_run.append(name)
            elif instance_type == 'trading' and trading_instance:
                specified_tests_to_run.append(name)
    else:
        specified_tests_to_run = [name for name in test_names if name in all_tests_info]

    if not specified_tests_to_run:
        dbg_warning(f"No valid trading tests specified or found (or instances missing for 'all') in: {test_names}")
        return {"total": 0, "passed": 0, "failed": 0}

    dbg_info(f"=== Starting Trading Tests ({', '.join(specified_tests_to_run)}) ===")
    total_passed = 0
    total_run = 0

    for name in specified_tests_to_run:
        test_func, instance_type = all_tests_info[name]
        instance_to_pass = None
        can_run_test = False

        if instance_type == 'evaluate':
            if evaluate_instance:
                instance_to_pass = evaluate_instance
                can_run_test = True
            else:
                dbg_warning(f"Skipping test [{name}]: Evaluate instance not provided.")
        elif instance_type == 'trading':
            if trading_instance:
                instance_to_pass = trading_instance
                can_run_test = True
            else:
                dbg_warning(f"Skipping test [{name}]: Trading instance not provided.")
        
        if can_run_test:
            total_run +=1
            dbg_trace(f"Executing test: {name}")
            try:
                # Pass the appropriate instance to each test function
                # Mocks are handled by @patch decorators on the test functions themselves
                dbg_info(instance_to_pass)
                result = test_func(instance_to_pass)
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
        else:
            results[name] = "SKIPPED"


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


