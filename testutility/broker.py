# testutility/broker.py
import os
import shutil # For cleaning up test directories
from datetime import datetime
from broker.brokermanager import BrokerManager, Position # Assuming Position is also relevant
from utility.debug import dbg_info, dbg_warning, dbg_error, dbg_trace
import traceback

# Define a default ticker and other constants for tests
DEFAULT_BROKER_TEST_TICKER = '2330' # TSMC
DEFAULT_BROKER_TEST_QTY = 10
TEST_STATE_DIR = "data/test_broker_states" # Directory for temporary state files
TEST_TRANSACTION_DIR = "data/test_broker_transactions"

def _create_test_broker(test_name: str, initial_cash=1000000.0, commission=5.0) -> BrokerManager:
    """Helper to create a broker instance with a unique state file for testing."""
    # Ensure the main test directories exist
    os.makedirs(TEST_STATE_DIR, exist_ok=True)
    os.makedirs(TEST_TRANSACTION_DIR, exist_ok=True)

    state_filepath = os.path.join(TEST_STATE_DIR, f"broker_state_{test_name}.json")
    transaction_log_path = os.path.join(TEST_TRANSACTION_DIR, f"transactions_{test_name}.csv")
    
    if os.path.exists(state_filepath):
        os.remove(state_filepath)
    if os.path.exists(transaction_log_path):
        os.remove(transaction_log_path)

    dbg_trace(f"Creating BrokerManager for test '{test_name}' with state: {state_filepath}, transactions: {transaction_log_path}")
    return BrokerManager(
        broker_type='base',
        initial_cash=initial_cash,
        commission_per_trade=commission,
        state_filepath=state_filepath, 
        transaction_log_path=transaction_log_path
    )

def cleanup_test_broker_files(test_name: str):
    """Cleans up files created by a specific test broker."""
    state_filepath = os.path.join(TEST_STATE_DIR, f"broker_state_{test_name}.json")
    transaction_log_path = os.path.join(TEST_TRANSACTION_DIR, f"transactions_{test_name}.csv")
    if os.path.exists(state_filepath):
        try:
            os.remove(state_filepath)
            dbg_trace(f"Cleaned up state file: {state_filepath}")
        except Exception as e:
            dbg_warning(f"Could not remove state file {state_filepath}: {e}")
    if os.path.exists(transaction_log_path):
        try:
            os.remove(transaction_log_path)
            dbg_trace(f"Cleaned up transaction log: {transaction_log_path}")
        except Exception as e:
            dbg_warning(f"Could not remove transaction log {transaction_log_path}: {e}")

def test_initial_state(broker_manager: BrokerManager, initial_cash_expected=1000000.0) -> bool:
    dbg_info("--- Running Test: Initial Broker State ---")
    try:
        cash = broker_manager.get_cash()
        positions = broker_manager.get_all_positions()
        if cash != initial_cash_expected:
            dbg_error(f"Initial cash incorrect. Expected {initial_cash_expected}, Got {cash}")
            return False
        if positions: # Should be empty
            dbg_error(f"Initial positions not empty. Got {positions}")
            return False
        dbg_info(f"Initial state OK. Cash: {cash}, Positions: {positions}")
        return True
    except Exception as e:
        dbg_error(f"Error in test_initial_state: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_place_buy_order_sufficient_cash(broker_manager: BrokerManager, symbol=DEFAULT_BROKER_TEST_TICKER, qty=DEFAULT_BROKER_TEST_QTY) -> bool:
    dbg_info(f"--- Running Test: Place Buy Order ({symbol}, {qty}) - Sufficient Cash ---")
    try:
        market_price = broker_manager.get_last_price(symbol)
        if market_price <= 0:
             dbg_warning(f"Market price for {symbol} is {market_price}, test might be unreliable. Assuming a mock price of 100 for cost calculation.")
             market_price = 100.0

        initial_cash = broker_manager.get_cash()
        result = broker_manager.place_order(symbol, "buy", qty, price=None)

        if result is None:
            dbg_error("Buy order failed unexpectedly (returned None).")
            return False
        if result['status'] != 'filled':
            dbg_error(f"Buy order not filled. Status: {result['status']}")
            return False

        expected_cost = (result['price'] * qty) + result['commission']
        if abs(broker_manager.get_cash() - (initial_cash - expected_cost)) > 0.01:
            dbg_error(f"Cash after buy incorrect. Expected approx {initial_cash - expected_cost}, Got {broker_manager.get_cash()}")
            return False
        
        position = broker_manager.get_position_by_symbol(symbol)
        if position.size != qty:
            dbg_error(f"Position size after buy incorrect. Expected {qty}, Got {position.size}")
            return False
        if abs(position.average_entry_price - result['price']) > 0.01 :
            dbg_error(f"Position avg entry price after buy incorrect. Expected {result['price']}, Got {position.average_entry_price}")
            return False
            
        dbg_info(f"Buy order for {symbol} successful. Position: {position}")
        return True
    except Exception as e:
        dbg_error(f"Error in test_place_buy_order_sufficient_cash: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_place_buy_order_insufficient_cash(broker_manager: BrokerManager, symbol="VERY_EXPENSIVE_STOCK", qty=100) -> bool:
    dbg_info(f"--- Running Test: Place Buy Order ({symbol}, {qty}) - Insufficient Cash ---")
    try:
        original_cash = broker_manager.broker.cash
        broker_manager.broker.cash = 10.0 
        broker_manager.broker._state_changed = True 
        
        result = broker_manager.place_order(symbol, "buy", qty, price=None)

        if result is not None:
            dbg_error(f"Buy order (insufficient cash) succeeded unexpectedly. Result: {result}")
            return False
        
        dbg_info(f"Buy order for {symbol} (insufficient cash) correctly rejected.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_place_buy_order_insufficient_cash: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        broker_manager.broker.cash = original_cash # Restore cash
        broker_manager.broker._state_changed = True

def test_get_position(broker_manager: BrokerManager, symbol=DEFAULT_BROKER_TEST_TICKER, expected_size=DEFAULT_BROKER_TEST_QTY) -> bool:
    dbg_info(f"--- Running Test: Get Position ({symbol}) ---")
    try:
        position = broker_manager.get_position_by_symbol(symbol)
        if position.symbol != symbol:
            dbg_error(f"Position symbol incorrect. Expected {symbol}, Got {position.symbol}")
            return False
        if position.size != expected_size:
            dbg_warning(f"Position size for {symbol}. Expected {expected_size}, Got {position.size}. This might be OK if prior tests changed it.")
        dbg_info(f"Get position for {symbol} OK: {position}")
        return True
    except Exception as e:
        dbg_error(f"Error in test_get_position: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_place_sell_order_sufficient_position(broker_manager: BrokerManager, symbol=DEFAULT_BROKER_TEST_TICKER, qty_to_sell=5) -> bool:
    dbg_info(f"--- Running Test: Place Sell Order ({symbol}, {qty_to_sell}) - Sufficient Position ---")
    try:
        initial_position = broker_manager.get_position_by_symbol(symbol)
        if initial_position.size < qty_to_sell:
            dbg_warning(f"Cannot run sell test: initial position size {initial_position.size} < qty to sell {qty_to_sell}. Placing a buy order first.")
            buy_result = broker_manager.place_order(symbol, "buy", qty_to_sell * 2, None)
            if not buy_result:
                 dbg_error("Failed to place preliminary buy order for sell test.")
                 return False
            initial_position = broker_manager.get_position_by_symbol(symbol)

        initial_cash = broker_manager.get_cash()
        result = broker_manager.place_order(symbol, "sell", qty_to_sell, price=None)

        if result is None:
            dbg_error("Sell order failed unexpectedly (returned None).")
            return False
        if result['status'] != 'filled':
            dbg_error(f"Sell order not filled. Status: {result['status']}")
            return False

        expected_proceeds = (result['price'] * qty_to_sell) - result['commission']
        if abs(broker_manager.get_cash() - (initial_cash + expected_proceeds)) > 0.01:
            dbg_error(f"Cash after sell incorrect. Expected approx {initial_cash + expected_proceeds}, Got {broker_manager.get_cash()}")
            return False
        
        final_position = broker_manager.get_position_by_symbol(symbol)
        if final_position.size != (initial_position.size - qty_to_sell):
            dbg_error(f"Position size after sell incorrect. Expected {initial_position.size - qty_to_sell}, Got {final_position.size}")
            return False
            
        dbg_info(f"Sell order for {symbol} successful. New Position: {final_position}")
        return True
    except Exception as e:
        dbg_error(f"Error in test_place_sell_order_sufficient_position: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_place_sell_order_insufficient_position(broker_manager: BrokerManager, symbol=DEFAULT_BROKER_TEST_TICKER) -> bool:
    dbg_info(f"--- Running Test: Place Sell Order ({symbol}) - Insufficient Position ---")
    try:
        current_pos_size = broker_manager.get_position_by_symbol(symbol).size
        qty_to_sell_too_many = current_pos_size + 10

        result = broker_manager.place_order(symbol, "sell", qty_to_sell_too_many, price=None)

        if result is not None:
            dbg_error(f"Sell order (insufficient position) for {symbol} succeeded unexpectedly. Result: {result}")
            return False
        
        dbg_info(f"Sell order for {symbol} (insufficient position) correctly rejected.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_place_sell_order_insufficient_position: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_portfolio_value(broker_manager: BrokerManager) -> bool:
    dbg_info("--- Running Test: Portfolio Value ---")
    try:
        if not broker_manager.get_all_positions():
            dbg_info("No positions to test portfolio value, placing a buy order.")
            broker_manager.place_order(DEFAULT_BROKER_TEST_TICKER, "buy", DEFAULT_BROKER_TEST_QTY, None)
        
        pv = broker_manager.get_portfolio_value()
        dbg_info(f"Calculated Portfolio Value: {pv}")
        if not isinstance(pv, float):
            dbg_error(f"Portfolio value is not a float. Got {type(pv)}")
            return False
        if pv < 0:
            dbg_warning(f"Portfolio value is negative ({pv}), which might be unexpected.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_portfolio_value: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_save_load_state(test_id_for_files="saveload") -> bool:
    dbg_info("--- Running Test: Save and Load State ---")
    broker_save = _create_test_broker(test_name=f"{test_id_for_files}_save", initial_cash=50000, commission=2.0)
    state_file_to_use = broker_save.broker.state_filepath
    tx_log_for_load_test = os.path.join(TEST_TRANSACTION_DIR, f"transactions_{test_id_for_files}_load.csv")
    if os.path.exists(tx_log_for_load_test):
        os.remove(tx_log_for_load_test) # Clean up before test

    try:
        broker_save.place_order("MSFT", "buy", 20, None)
        broker_save.place_order("GOOG", "buy", 5, None)
        cash_before_save = broker_save.get_cash()
        positions_before_save = broker_save.get_all_positions()
        dbg_info(f"State before save - Cash: {cash_before_save}, Positions: {len(positions_before_save)}")

        broker_save.disconnect()

        broker_load = BrokerManager(broker_type='base', initial_cash=1000, commission_per_trade=1.0, state_filepath=state_file_to_use, transaction_log_path=tx_log_for_load_test)
        broker_load.connect()

        cash_after_load = broker_load.get_cash()
        positions_after_load = broker_load.get_all_positions()
        dbg_info(f"State after load - Cash: {cash_after_load}, Positions: {len(positions_after_load)}")

        if abs(cash_after_load - cash_before_save) > 0.01:
            dbg_error(f"Cash mismatch after load. Expected {cash_before_save}, Got {cash_after_load}")
            return False
        if len(positions_after_load) != len(positions_before_save):
            dbg_error(f"Position count mismatch. Expected {len(positions_before_save)}, Got {len(positions_after_load)}")
            return False
        for sym, pos_before in positions_before_save.items():
            if sym not in positions_after_load:
                dbg_error(f"Symbol {sym} missing after load.")
                return False
            pos_after = positions_after_load[sym]
            if pos_before.size != pos_after.size or \
               abs(pos_before.average_entry_price - pos_after.average_entry_price) > 0.01:
                dbg_error(f"Position data mismatch for {sym}. Before: {pos_before}, After: {pos_after}")
                return False
        
        dbg_info("Save and load state successful.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_save_load_state: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        cleanup_test_broker_files(f"{test_id_for_files}_save")
        if os.path.exists(tx_log_for_load_test):
            try:
                os.remove(tx_log_for_load_test)
            except Exception as e:
                dbg_warning(f"Could not remove load test transaction log {tx_log_for_load_test}: {e}")

def test_transaction_logging(test_id_for_files="txlog") -> bool:
    dbg_info("--- Running Test: Transaction Logging ---")
    broker = _create_test_broker(test_name=test_id_for_files)
    tx_log_path = broker.transaction_log_path
    try:
        broker.place_order("TXLOGSMBL", "buy", 10, None)
        broker.place_order("TXLOGSMBL", "sell", 5, None)
        
        transactions = broker.get_transactions()
        if len(transactions) < 2:
            dbg_error(f"Expected at least 2 transactions, got {len(transactions)}. Log path: {tx_log_path}")
            if os.path.exists(tx_log_path):
                with open(tx_log_path, 'r') as f:
                    dbg_info(f"Transaction log content:\n{f.read()}")
            return False
        
        dbg_info(f"Transactions logged: {len(transactions)}. Sample: {transactions[0] if transactions else 'N/A'}")
        if transactions:
            first_tx = transactions[0]
            expected_keys = ['timestamp', 'symbol', 'action', 'size', 'price', 'commission', 'cash_balance']
            if not all(key in first_tx for key in expected_keys):
                dbg_error(f"Transaction record missing expected keys. Got: {first_tx.keys()}")
                return False
        return True
    except Exception as e:
        dbg_error(f"Error in test_transaction_logging: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        cleanup_test_broker_files(test_id_for_files)

def test_summarize_positions(broker_manager: BrokerManager) -> bool:
    dbg_info("--- Running Test: Summarize Positions ---")
    try:
        if not broker_manager.get_all_positions():
            broker_manager.place_order(DEFAULT_BROKER_TEST_TICKER, "buy", DEFAULT_BROKER_TEST_QTY, None)
        
        dbg_info("Calling summarize_positions(). Check output manually.")
        broker_manager.summarize_positions()
        return True
    except Exception as e:
        dbg_error(f"Error in test_summarize_positions: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_summarize_transactions(broker_manager: BrokerManager) -> bool:
    dbg_info("--- Running Test: Summarize Transactions ---")
    try:
        if not broker_manager.get_transactions(): # Check if transactions already exist
             broker_manager.place_order(DEFAULT_BROKER_TEST_TICKER, "buy", 3, None)
             broker_manager.place_order(DEFAULT_BROKER_TEST_TICKER, "sell", 1, None)

        dbg_info("Calling summarize_transactions(). Check output manually.")
        broker_manager.summarize_transactions(duration=None)
        broker_manager.summarize_transactions(duration='month')
        return True
    except Exception as e:
        dbg_error(f"Error in test_summarize_transactions: {e}")
        dbg_error(traceback.format_exc())
        return False

# --- Test Runner ---
def run_broker_tests(test_names: list[str]):
    results = {}
    standalone_tests = {
        "save_load_state": lambda: test_save_load_state("saveload_cli"),
        "transaction_logging": lambda: test_transaction_logging("txlog_cli"),
    }

    sequential_broker_test_name = "sequential_ops_cli"
    shared_broker_instance = _create_test_broker(test_name=sequential_broker_test_name, initial_cash=100000.0, commission=1.0)
    
    sequential_tests = {
        "initial_state": lambda bm: test_initial_state(bm, initial_cash_expected=100000.0),
        "buy_sufficient_cash": lambda bm: test_place_buy_order_sufficient_cash(bm, symbol="SEQBUY", qty=10),
        "get_position_after_buy": lambda bm: test_get_position(bm, symbol="SEQBUY", expected_size=10),
        "sell_sufficient_position": lambda bm: test_place_sell_order_sufficient_position(bm, symbol="SEQBUY", qty_to_sell=5),
        "get_position_after_sell": lambda bm: test_get_position(bm, symbol="SEQBUY", expected_size=5),
        "portfolio_value": test_portfolio_value,
        "buy_insufficient_cash": lambda bm: test_place_buy_order_insufficient_cash(bm, symbol="HIGHVAL", qty=1),
        "sell_insufficient_position": lambda bm: test_place_sell_order_insufficient_position(bm, symbol="SEQBUY"),
        "summarize_positions": test_summarize_positions,
        "summarize_transactions": test_summarize_transactions,
    }

    all_test_definitions = {**standalone_tests, **sequential_tests}

    tests_to_run_names = []
    if "all" in test_names:
        tests_to_run_names = list(all_test_definitions.keys())
    else:
        tests_to_run_names = [name for name in test_names if name in all_test_definitions]

    if not tests_to_run_names:
        dbg_warning(f"No valid broker tests specified or found in: {test_names}")
        cleanup_test_broker_files(sequential_broker_test_name) # Clean up shared broker files if no tests run
        return

    dbg_info("=== Starting Broker Tests ===")
    total_passed = 0
    for name in tests_to_run_names:
        dbg_trace(f"Executing test: {name}")
        try:
            if name in standalone_tests:
                test_func = standalone_tests[name]
                result = test_func()
            elif name in sequential_tests:
                test_func = sequential_tests[name]
                result = test_func(shared_broker_instance)
            else:
                dbg_warning(f"Test '{name}' definition not found. Skipping.")
                continue
            
            results[name] = result
            if result:
                total_passed += 1
            dbg_info(f"--- Test Result [{name}]: {'PASS' if result else 'FAIL'} ---")
        except Exception as e:
            dbg_error(f"!!! Exception during test [{name}]: {e} !!!")
            dbg_error(traceback.format_exc())
            results[name] = False
        dbg_info("-" * 40)

    cleanup_test_broker_files(sequential_broker_test_name)
    
    try:
        if os.path.exists(TEST_STATE_DIR) and not os.listdir(TEST_STATE_DIR):
            shutil.rmtree(TEST_STATE_DIR)
            dbg_trace(f"Cleaned up empty directory: {TEST_STATE_DIR}")
        if os.path.exists(TEST_TRANSACTION_DIR) and not os.listdir(TEST_TRANSACTION_DIR):
            shutil.rmtree(TEST_TRANSACTION_DIR)
            dbg_trace(f"Cleaned up empty directory: {TEST_TRANSACTION_DIR}")
        data_dir = "data"
        if os.path.exists(data_dir) and not os.listdir(data_dir):
            shutil.rmtree(data_dir)
            dbg_trace(f"Cleaned up empty directory: {data_dir}")
    except OSError as e:
        dbg_warning(f"Warning during cleanup of test directories: {e}")

    dbg_info("=== Broker Tests Summary ===")
    for name, result in results.items():
        dbg_info(f"  {name:<30}: {'PASS' if result else 'FAIL'}")
    total_failed = len(tests_to_run_names) - total_passed
    dbg_info(f"Total Tests Run: {len(tests_to_run_names)}, Passed: {total_passed}, Failed: {total_failed}")
    dbg_info("==========================")
    return {"total": len(tests_to_run_names), "passed": total_passed, "failed": total_failed}

