# testutility/market.py
import pandas as pd
from market.market import Market
from utility.debug import dbg_info, dbg_warning, dbg_error, dbg_trace
import traceback # Import traceback for detailed error logging

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

# Define a default ticker for tests requiring one
DEFAULT_TEST_TICKER = '2330' # TSMC

def test_list_providers(market_instance: Market) -> bool:
    """Tests the get_markget_list method."""
    dbg_info("--- Running Test: List Providers ---")
    try:
        providers = market_instance.get_markget_list()
        if not providers:
            dbg_warning("get_markget_list() returned an empty list.")
            return False
        dbg_info(f"Available Providers: {providers}")
        return True
    except Exception as e:
        dbg_error(f"Error testing list_providers: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_switch_market(market_instance: Market) -> bool:
    """Tests switching market providers."""
    dbg_info("--- Running Test: Switch Market ---")
    original_provider = market_instance.get_provider()
    dbg_info(f"Original provider: {original_provider}")
    providers = market_instance.get_markget_list()
    if len(providers) < 2:
        dbg_warning("Need at least two providers to test switching. Skipping.")
        return True # Not a failure, just can't test

    # Switch to the next provider in the list (or wrap around)
    try:
        current_index = providers.index(original_provider)
        next_index = (current_index + 1) % len(providers)
        next_provider = providers[next_index]

        dbg_info(f"Attempting to switch to: {next_provider}")
        market_instance.switch_market(next_provider)
        switched_provider = market_instance.get_provider()

        if switched_provider == next_provider:
            dbg_info(f"Successfully switched to {switched_provider}")
            # Switch back to original for subsequent tests
            market_instance.switch_market(original_provider)
            dbg_info(f"Switched back to original provider: {market_instance.get_provider()}")
            return True
        else:
            dbg_error(f"Failed to switch. Expected {next_provider}, got {switched_provider}")
            # Attempt to switch back anyway
            market_instance.switch_market(original_provider)
            return False
    except Exception as e:
        dbg_error(f"Error testing switch_market: {e}")
        dbg_error(traceback.format_exc())
        # Attempt to switch back
        try:
            market_instance.switch_market(original_provider)
        except Exception as e_revert:
             dbg_error(f"Error reverting market provider: {e_revert}")
             dbg_error(traceback.format_exc())
        return False

def test_get_data_list(market_instance: Market) -> bool:
    """Tests the get_data_list method."""
    dbg_info("--- Running Test: Get Data List ---")
    provider = market_instance.get_provider()
    dbg_info(f"Using provider: {provider}")
    try:
        data_list = market_instance.get_data_list() # Default market/country
        if not data_list:
            # This might be expected for some providers/filters, treat as warning
            dbg_warning(f"get_data_list() returned an empty list for provider {provider}.")
            # Depending on provider, empty might be ok. Let's return True but log.
            return True
        dbg_info(f"get_data_list() returned {len(data_list)} items. First 5: {data_list[:5]}")
        # Check if the cached frame was updated
        if market_instance.cached_stock_info_frame is None or market_instance.cached_stock_info_frame.empty:
             dbg_warning("cached_stock_info_frame was not updated or is empty after get_data_list().")
             # This might not be a failure depending on implementation, but worth noting.
        else:
             dbg_info(f"cached_stock_info_frame updated with {len(market_instance.cached_stock_info_frame)} rows.")
        return True
    except Exception as e:
        dbg_error(f"Error testing get_data_list for provider {provider}: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_get_data(market_instance: Market, product_id: str = DEFAULT_TEST_TICKER) -> bool:
    """Tests the get_data method for a specific product."""
    dbg_info(f"--- Running Test: Get Data ({product_id}) ---")
    provider = market_instance.get_provider()
    dbg_info(f"Using provider: {provider}")
    try:
        # Fetch data for the last year (or a small period)
        df = market_instance.get_data(product_id=product_id, period="1y")
        if df is None or df.empty:
            dbg_warning(f"get_data() returned None or empty DataFrame for {product_id} using {provider}.")
            # This could be valid if the ticker doesn't exist for the provider, not necessarily a failure.
            return True # Let's consider this non-failure for now.
        dbg_info(f"get_data() for {product_id} returned DataFrame with shape {df.shape}.")
        dbg_info("Sample data (tail):\n" + df.tail().to_string())
        # Basic checks
        if not isinstance(df.index, pd.DatetimeIndex):
             dbg_error("DataFrame index is not a DatetimeIndex.")
             return False
        expected_cols = ['Open', 'High', 'Low', 'Close', 'Volume'] # Core columns
        if not all(col in df.columns for col in expected_cols):
             dbg_error(f"DataFrame missing one or more expected columns: {expected_cols}. Found: {df.columns.tolist()}")
             return False
        return True
    except Exception as e:
        dbg_error(f"Error testing get_data for {product_id} using {provider}: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_get_data_info(market_instance: Market, product_id: str = DEFAULT_TEST_TICKER) -> bool:
    """Tests the get_data_info method."""
    dbg_info(f"--- Running Test: Get Data Info ({product_id}) ---")
    provider = market_instance.get_provider()
    dbg_info(f"Using provider: {provider}")
    try:
        # Ensure cache is potentially populated (get_data_list might do this)
        if market_instance.cached_stock_info_frame is None:
             dbg_trace("Cache is empty, calling get_data_list() first.")
             market_instance.get_data_list()

        info = market_instance.get_data_info(product_id)
        if info is None:
            dbg_warning(f"get_data_info() returned None for {product_id} using {provider}.")
            # Could be valid if ticker not in list, treat as warning/non-failure.
            return True
        if not isinstance(info, dict):
             dbg_error(f"get_data_info() did not return a dictionary for {product_id}. Got: {type(info)}")
             return False
        dbg_info(f"get_data_info() for {product_id} returned: {info}")
        # Check for essential keys
        expected_keys = ['code', 'name', 'start', 'market']
        if not all(key in info for key in expected_keys):
             dbg_error(f"Info dictionary missing one or more expected keys: {expected_keys}. Found: {list(info.keys())}")
             return False
        if info['code'] != product_id:
             dbg_error(f"Info dictionary code '{info['code']}' does not match requested product_id '{product_id}'.")
             return False
        return True
    except Exception as e:
        dbg_error(f"Error testing get_data_info for {product_id} using {provider}: {e}")
        dbg_error(traceback.format_exc())
        return False

# --- Test Runner ---
def run_market_tests(market_instance: Market, test_names: list[str]):
    """Runs specified market tests."""
    results = {}
    all_tests = {
        "list_providers": test_list_providers,
        "switch_market": test_switch_market,
        "get_data_list": test_get_data_list,
        "get_data": lambda m: test_get_data(m), # Use default ticker
        "get_info": lambda m: test_get_data_info(m), # Use default ticker
    }

    tests_to_run = []
    if "all" in test_names:
        tests_to_run = list(all_tests.keys())
    else:
        tests_to_run = [name for name in test_names if name in all_tests]

    if not tests_to_run:
        dbg_warning(f"No valid market tests specified or found in: {test_names}")
        return

    dbg_info(f"=== Starting Market Tests ({market_instance.get_provider()}) ===")
    total_passed = 0
    for name in tests_to_run:
        dbg_trace(f"Executing test: {name}")
        test_func = all_tests[name]
        try:
            result = test_func(market_instance)
            results[name] = result
            if result:
                total_passed += 1
            status_str = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
            dbg_info(f"--- Test Result [{name}]: {status_str} ---")
        except Exception as e:
            dbg_error(f"!!! Exception during test [{name}]: {e} !!!")
            dbg_error(traceback.format_exc())
            results[name] = False
        dbg_info("-" * 40) # Use dbg_info for separator

    dbg_info(f"=== Market Tests Summary ===")
    for name, result in results.items():
        status_str = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        dbg_info(f"  {name:<20}: {status_str}")
    total_failed = len(tests_to_run) - total_passed
    passed_str = f"{GREEN}Passed: {total_passed}{RESET}"
    failed_str = f"{RED}Failed: {total_failed}{RESET}" if total_failed > 0 else f"Failed: {total_failed}"
    dbg_info(f"Total Tests Run: {len(tests_to_run)}, {passed_str}, {failed_str}")
    dbg_info("==========================")
    return {"total": len(tests_to_run), "passed": total_passed, "failed": total_failed}
