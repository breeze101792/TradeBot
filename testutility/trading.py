# testutility/trading.py
import traceback
from datetime import date, timedelta

# Local file
from trading.evaluate import Evaluate
from utility.debug import dbg_info, dbg_warning, dbg_error, dbg_trace
from core.config import AppConfigManager # Evaluate uses this

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

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


# --- Test Runner ---
def run_trading_tests(evaluate_instance: Evaluate, test_names: list[str]):
    """Runs specified trading tests."""
    results = {}
    all_tests = {
        "buying_evaluation": test_buying_evaluation,
        "selling_evaluation": test_selling_evaluation,
    }

    tests_to_run = []
    if "all" in test_names:
        tests_to_run = list(all_tests.keys())
    else:
        tests_to_run = [name for name in test_names if name in all_tests]

    if not tests_to_run:
        dbg_warning(f"No valid trading tests specified or found in: {test_names}")
        return {"total": 0, "passed": 0, "failed": 0} # Return empty summary

    dbg_info(f"=== Starting Trading Tests ===")
    total_passed = 0
    for name in tests_to_run:
        dbg_trace(f"Executing test: {name}")
        test_func = all_tests[name]
        try:
            # Pass the evaluate_instance to each test function
            result = test_func(evaluate_instance)
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
        status_str = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        dbg_info(f"  {name:<25}: {status_str}") # Adjusted spacing
    total_failed = len(tests_to_run) - total_passed
    passed_str = f"{GREEN}Passed: {total_passed}{RESET}"
    failed_str = f"{RED}Failed: {total_failed}{RESET}" if total_failed > 0 else f"Failed: {total_failed}"
    dbg_info(f"Total Tests Run: {len(tests_to_run)}, {passed_str}, {failed_str}")
    dbg_info("==========================")
    return {"total": len(tests_to_run), "passed": total_passed, "failed": total_failed}


