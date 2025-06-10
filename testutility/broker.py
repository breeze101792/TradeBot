# testutility/broker.py
import os
import shutil # For cleaning up test directories
from datetime import datetime,timedelta
import time
import traceback
import io # New import for capturing stdout
import contextlib # New import for redirecting stdout
from unittest.mock import patch, MagicMock # New imports for mocking
from typing import Optional

from utility.debug import dbg_info, dbg_warning, dbg_error, dbg_trace
from broker.brokermanager import BrokerManager, Position # Assuming Position is also relevant
from broker.order.event import Event
from broker.order.ordertracker import OrderTracker
from broker.order.constant import OrderStatus, OrderAction, OrderPrice
from broker.brokermanager import event_callback as original_event_callback # Import the original function to wrap

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

# Define a default ticker and other constants for tests
DEFAULT_BROKER_TEST_TICKER = '2330' # TSMC
DEFAULT_BROKER_TEST_QTY = 10
DEFAULT_BROKER_TYPE = 'mock'
TEST_STATE_DIR = "data/test_broker_states" # Directory for temporary state files
TEST_TRANSACTION_DIR = "data/test_broker_transactions"

def _setup_test_broker_manager(test_name: str, initial_cash=1000000.0, commission_rate=0.001, 
                               state_filepath: Optional[str] = None, transaction_log_path: Optional[str] = None, clean_file = True):
    """Helper to initialize the BrokerManager class for testing."""
    # Ensure the main test directories exist
    os.makedirs(TEST_STATE_DIR, exist_ok=True)
    os.makedirs(TEST_TRANSACTION_DIR, exist_ok=True)

    # Use provided paths or generate default ones
    actual_state_filepath = state_filepath if state_filepath else os.path.join(TEST_STATE_DIR, f"broker_state_{test_name}.json")
    actual_transaction_log_path = transaction_log_path if transaction_log_path else os.path.join(TEST_TRANSACTION_DIR, f"transactions_{test_name}.csv")
    
    if clean_file is True:
        if os.path.exists(actual_state_filepath):
            os.remove(actual_state_filepath)
        if os.path.exists(actual_transaction_log_path):
            os.remove(actual_transaction_log_path)

    dbg_trace(f"Initializing BrokerManager for test '{test_name}' with state: {actual_state_filepath}, transactions: {actual_transaction_log_path}")
    BrokerManager.initialize(
        broker_type=DEFAULT_BROKER_TYPE,
        initial_cash=initial_cash,
        commission_rate=commission_rate,
        state_filepath=actual_state_filepath, 
        transaction_log_path=actual_transaction_log_path,
        simulation = True
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

def test_initial_state(test_id: str, initial_cash_expected=1000000.0) -> bool:
    dbg_info("--- Running Test: Initial Broker State ---")
    _setup_test_broker_manager(test_name=test_id, initial_cash=initial_cash_expected)
    broker_manager = BrokerManager()
    try:
        cash = broker_manager.get_balance()
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
    finally:
        BrokerManager.finalize()
        cleanup_test_broker_files(test_id)

def test_place_buy_order_sufficient_cash(test_id: str, symbol=DEFAULT_BROKER_TEST_TICKER, qty=DEFAULT_BROKER_TEST_QTY) -> bool:
    dbg_info(f"--- Running Test: Place Buy Order ({symbol}, {qty}) - Sufficient Cash ---")
    _setup_test_broker_manager(test_name=test_id)
    broker_manager = BrokerManager()
    try:
        market_price = broker_manager.get_last_price(symbol, OrderPrice.ASK)
        if market_price <= 0:
             dbg_warning(f"Market price for {symbol} is {market_price}, test might be unreliable. Assuming a mock price of 100 for cost calculation.")

        initial_cash = broker_manager.get_balance()
        initial_transactions_count = len(broker_manager.get_transactions())

        broker_manager.place_order(symbol, OrderAction.BUY, qty, price=None) # No longer capture return value

        # Verify that a transaction was logged
        transactions = broker_manager.get_transactions()
        if len(transactions) <= initial_transactions_count:
            dbg_error("Buy order did not result in a new transaction.")
            return False
        
        latest_tx = transactions[-1]
        if latest_tx['symbol'] != symbol or latest_tx['action'] != OrderAction.BUY.value:
            dbg_error(f"Latest transaction is not the expected buy order for {symbol}. Got: {latest_tx}")
            return False

        # Extract actual fill details from the transaction log
        try:
            filled_price = float(latest_tx['price'])
            commission = float(latest_tx['commission'])
        except ValueError:
            dbg_error(f"Failed to parse numeric values from latest transaction: {latest_tx}")
            return False

        expected_cost = (filled_price * qty) + commission
        
        if abs(broker_manager.get_balance() - (initial_cash - expected_cost)) > 0.01:
            dbg_error(f"Cash after buy incorrect. Expected approx {initial_cash - expected_cost}, Got {broker_manager.get_balance()}")
            return False
        
        position = broker_manager.get_position_by_symbol(symbol)
        if position.size != qty:
            dbg_error(f"Position size after buy incorrect. Expected {qty}, Got {position.size}")
            return False
        if abs(position.average_entry_price - filled_price) > 0.01 : # Use filled_price from log
            dbg_error(f"Position avg entry price after buy incorrect. Expected {filled_price}, Got {position.average_entry_price}")
            return False
            
        dbg_info(f"Buy order for {symbol} successful. Position: {position}")
        return True
    except Exception as e:
        dbg_error(f"Error in test_place_buy_order_sufficient_cash: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        BrokerManager.finalize()
        cleanup_test_broker_files(test_id)

def test_place_buy_order_insufficient_cash(test_id: str, symbol=DEFAULT_BROKER_TEST_TICKER, qty=100) -> bool:
    dbg_info(f"--- Running Test: Place Buy Order ({symbol}, {qty}) - Insufficient Cash ---")
    _setup_test_broker_manager(test_name=test_id)
    broker_manager = BrokerManager()
    original_cash_in_broker = broker_manager.broker.cash # Store original cash before modification
    initial_transactions_count = len(broker_manager.get_transactions())
    
    try:
        broker_manager.broker.cash = 10.0 
        broker_manager.broker._state_changed = True 
        
        # Place the order - it should fail, and we expect no change in state or new transaction
        broker_manager.place_order(symbol, OrderAction.BUY, qty, price=None) # No longer capture return value

        # Verify cash and positions are unchanged
        if abs(broker_manager.get_balance() - 10.0) > 0.01: # Should still be 10.0
            dbg_error(f"Cash changed after failed buy. Expected 10.0, Got {broker_manager.get_balance()}")
            return False
        
        if broker_manager.get_position_by_symbol(symbol).size != 0:
            dbg_error(f"Position created after failed buy. Got {broker_manager.get_position_by_symbol(symbol).size}")
            return False

        print(broker_manager.get_transactions())
        # Verify no new transaction was logged for this failed order
        if len(broker_manager.get_transactions()) != initial_transactions_count:
            dbg_error(f"Transaction logged for failed buy order. Expected {initial_transactions_count}, Got {len(broker_manager.get_transactions())}")
            return False

        dbg_info(f"Buy order for {symbol} (insufficient cash) correctly rejected.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_place_buy_order_insufficient_cash: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        broker_manager.broker.cash = original_cash_in_broker # Restore cash
        broker_manager.broker._state_changed = True
        BrokerManager.finalize()
        cleanup_test_broker_files(test_id)

def test_get_position(test_id: str, symbol=DEFAULT_BROKER_TEST_TICKER, expected_size=DEFAULT_BROKER_TEST_QTY) -> bool:
    dbg_info(f"--- Running Test: Get Position ({symbol}) ---")
    _setup_test_broker_manager(test_name=test_id)
    broker_manager = BrokerManager()
    try:
        initial_transactions_count = len(broker_manager.get_transactions())
        # Ensure there's a position to get
        broker_manager.place_order(symbol, OrderAction.BUY, expected_size, None)
        
        # Get the latest transaction to verify fill details for the setup order
        transactions = broker_manager.get_transactions()
        if len(transactions) <= initial_transactions_count:
            dbg_error("Setup buy order did not result in a new transaction.")
            return False
        latest_tx = transactions[-1]
        if latest_tx['symbol'] != symbol or latest_tx['action'] != OrderAction.BUY.value:
            dbg_error(f"Latest transaction is not the expected setup buy order for {symbol}. Got: {latest_tx}")
            return False
        
        try:
            filled_price = float(latest_tx['price'])
        except ValueError:
            dbg_error(f"Failed to parse price from latest transaction: {latest_tx}")
            return False

        position = broker_manager.get_position_by_symbol(symbol)
        if position is None:
            dbg_error(f"Position for {symbol} not found after placing order.")
            return False
        if position.symbol != symbol:
            dbg_error(f"Position symbol incorrect. Expected {symbol}, Got {position.symbol}")
            return False
        if position.size != expected_size:
            dbg_error(f"Position size for {symbol} incorrect. Expected {expected_size}, Got {position.size}.")
            return False
        # Verify average entry price based on the filled price from the transaction log
        if abs(position.average_entry_price - filled_price) > 0.01:
            dbg_error(f"Position avg entry price after buy incorrect. Expected {filled_price}, Got {position.average_entry_price}")
            return False

        dbg_info(f"Get position for {symbol} OK: {position}")
        return True
    except Exception as e:
        dbg_error(f"Error in test_get_position: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        BrokerManager.finalize()
        cleanup_test_broker_files(test_id)

def test_place_sell_order_sufficient_position(test_id: str, symbol=DEFAULT_BROKER_TEST_TICKER, qty_to_sell=5) -> bool:
    dbg_info(f"--- Running Test: Place Sell Order ({symbol}, {qty_to_sell}) - Sufficient Position ---")
    _setup_test_broker_manager(test_name=test_id)
    broker_manager = BrokerManager()
    try:
        # Ensure there's an initial position to sell from
        initial_buy_qty = DEFAULT_BROKER_TEST_QTY + qty_to_sell # Ensure enough to sell and still have some
        broker_manager.place_order(symbol, OrderAction.BUY, initial_buy_qty, None) # Setup buy
        
        initial_position_size = broker_manager.get_position_by_symbol(symbol).size
        initial_cash = broker_manager.get_balance()
        initial_transactions_count = len(broker_manager.get_transactions())

        broker_manager.place_order(symbol, OrderAction.SELL, qty_to_sell, price=None) # No longer capture return value

        # Get the latest transaction for sell details
        transactions = broker_manager.get_transactions()
        if len(transactions) <= initial_transactions_count:
            dbg_error("Sell order did not result in a new transaction.")
            return False
        latest_tx = transactions[-1]
        if latest_tx['symbol'] != symbol or latest_tx['action'] != OrderAction.SELL.value:
            dbg_error(f"Latest transaction is not the expected sell order for {symbol}. Got: {latest_tx}")
            return False

        try:
            filled_price = float(latest_tx['price'])
            commission = float(latest_tx['commission'])
        except ValueError:
            dbg_error(f"Failed to parse numeric values from latest transaction: {latest_tx}")
            return False

        expected_proceeds = (filled_price * qty_to_sell) - commission
        
        if abs(broker_manager.get_balance() - (initial_cash + expected_proceeds)) > 0.01:
            dbg_error(f"Cash after sell incorrect. Expected approx {initial_cash + expected_proceeds}, Got {broker_manager.get_balance()}")
            return False
        
        final_position = broker_manager.get_position_by_symbol(symbol)
        if final_position.size != (initial_position_size - qty_to_sell):
            dbg_error(f"Position size after sell incorrect. Expected {initial_position_size - qty_to_sell}, Got {final_position.size}")
            return False
            
        dbg_info(f"Sell order for {symbol} successful. New Position: {final_position}")
        return True
    except Exception as e:
        dbg_error(f"Error in test_place_sell_order_sufficient_position: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        BrokerManager.finalize()
        cleanup_test_broker_files(test_id)

def test_place_sell_order_insufficient_position(test_id: str, symbol=DEFAULT_BROKER_TEST_TICKER) -> bool:
    dbg_info(f"--- Running Test: Place Sell Order ({symbol}) - Insufficient Position ---")
    _setup_test_broker_manager(test_name=test_id)
    broker_manager = BrokerManager()
    
    initial_cash = broker_manager.get_balance()
    initial_transactions_count = len(broker_manager.get_transactions())

    # Use patch.object to mock the event_callback method of the broker_manager instance
    with patch.object(broker_manager.order_svc, 'event_callback', wraps=original_event_callback) as mock_event_callback:
        try:
            # Ensure there's a small initial position, but not enough for the sell
            broker_manager.place_order(symbol, OrderAction.BUY, 5, None) # Buy 5 shares
            
            # After the buy, update initial state for comparison
            initial_cash_after_buy = broker_manager.get_balance()
            initial_positions_after_buy = broker_manager.get_all_positions()
            initial_transactions_count_after_buy = len(broker_manager.get_transactions())

            current_pos_size = broker_manager.get_position_by_symbol(symbol).size
            qty_to_sell_too_many = current_pos_size + 10 # Try to sell more than available

            # Place the order that should fail
            broker_manager.place_order(symbol, OrderAction.SELL, qty_to_sell_too_many, price=None)

            # Verify cash and positions are unchanged from *after the initial buy*
            if abs(broker_manager.get_balance() - initial_cash_after_buy) > 0.01:
                dbg_error(f"Cash changed after failed sell. Expected {initial_cash_after_buy}, Got {broker_manager.get_balance()}")
                return False
            
            # Verify position size is unchanged for the symbol
            final_position = broker_manager.get_position_by_symbol(symbol)
            if final_position.size != current_pos_size:
                dbg_error(f"Position size changed after failed sell. Expected {current_pos_size}, Got {final_position.size}")
                return False

            # Verify no new transaction was logged for this failed order
            if len(broker_manager.get_transactions()) != initial_transactions_count_after_buy:
                dbg_error(f"Transaction logged for failed sell order. Expected {initial_transactions_count_after_buy}, Got {len(broker_manager.get_transactions())}")
                return False

            # Assert that an OrderFailed event was called
            failed_event_found = False
            for call_args, call_kwargs in mock_event_callback.call_args_list:
                if call_args and call_args[0] == Event.OrderFailed:
                    failed_event_found = True
                    order_tracker = call_args[1]
                    if not isinstance(order_tracker, OrderTracker):
                        dbg_error(f"OrderFailed event data is not OrderTracker type: {type(order_tracker)}")
                        return False
                    if order_tracker.symbol != symbol or order_tracker.action != OrderAction.SELL or order_tracker.size != qty_to_sell_too_many:
                        dbg_error(f"OrderFailed event details mismatch. Expected {symbol}, sell, {qty_to_sell_too_many}. Got {order_tracker.symbol}, {order_tracker.action}, {order_tracker.size}")
                        return False
                    if order_tracker.status != OrderStatus.REJECTED:
                        dbg_error(f"OrderFailed event status mismatch. Expected 'REJECTED', Got {order_tracker.status}")
                        return False
                    dbg_info(f"OrderFailed event correctly captured with reason: {order_tracker.reason}")
                    break
            
            if not failed_event_found:
                dbg_error("OrderFailed event was not triggered for insufficient position sell order.")
                return False

            dbg_info(f"Sell order for {symbol} (insufficient position) correctly rejected and event triggered.")
            return True
        except Exception as e:
            dbg_error(f"Error in test_place_sell_order_insufficient_position: {e}")
            dbg_error(traceback.format_exc())
            return False
        finally:
            cleanup_test_broker_files(test_id)

def test_portfolio_value(test_id: str) -> bool:
    dbg_info("--- Running Test: Portfolio Value ---")
    _setup_test_broker_manager(test_name=test_id)
    broker_manager = BrokerManager()
    try:
        if not broker_manager.get_all_positions():
            dbg_info("No positions to test portfolio value, placing a buy order.")
            broker_manager.place_order(DEFAULT_BROKER_TEST_TICKER, OrderAction.BUY, DEFAULT_BROKER_TEST_QTY, None)
        
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
    finally:
        BrokerManager.finalize()
        cleanup_test_broker_files(test_id)

def test_save_load_state(test_id: str) -> bool:
    dbg_info("--- Running Test: Save and Load State ---")
    state_file_for_save = os.path.join(TEST_STATE_DIR, f"broker_state_{test_id}_save.json")
    tx_log_for_save = os.path.join(TEST_TRANSACTION_DIR, f"transactions_{test_id}_save.csv")
    tx_log_for_load = os.path.join(TEST_TRANSACTION_DIR, f"transactions_{test_id}_load.csv")

    # Clean up files before starting
    if os.path.exists(state_file_for_save): os.remove(state_file_for_save)
    if os.path.exists(tx_log_for_save): os.remove(tx_log_for_save)
    if os.path.exists(tx_log_for_load): os.remove(tx_log_for_load)

    try:
        # --- Part 1: Save State ---
        _setup_test_broker_manager(
            test_name=f"{test_id}", 
            initial_cash=50000, 
            commission_rate=0.001,
            state_filepath=state_file_for_save, # Explicitly pass paths
            transaction_log_path=tx_log_for_save
        )
        broker_save_instance = BrokerManager() # Get the instance that uses the class-level broker

        broker_save_instance.place_order(DEFAULT_BROKER_TEST_TICKER, OrderAction.BUY, 20, None)
        broker_save_instance.place_order(DEFAULT_BROKER_TEST_TICKER, OrderAction.BUY, 5, None)
        cash_before_save = broker_save_instance.get_balance()
        positions_before_save = broker_save_instance.get_all_positions()
        dbg_info(f"State before save - Cash: {cash_before_save}, Positions: {len(positions_before_save)}")

        # wait for callback event to log transaction.
        # time.sleep(1)

        # --- Part 2: Load State ---
        # Initialize BrokerManager again, pointing to the saved state file
        _setup_test_broker_manager(
            test_name=f"{test_id}", # Use a different test_name for cleanup purposes if needed, but state_filepath is key
            initial_cash=1000, # These initial values are ignored if state_filepath exists and loads
            commission_rate=1.0,
            state_filepath=state_file_for_save, # Crucially, load from the *saved* file
            transaction_log_path=tx_log_for_load, # New transaction log for the loaded session
            clean_file = False
        )
        broker_load_instance = BrokerManager() # Get the instance that uses the class-level broker

        cash_after_load = broker_load_instance.get_balance()
        positions_after_load = broker_load_instance.get_all_positions()
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
        BrokerManager.finalize() # Finalize the last initialized broker
        # cleanup_test_broker_files(f"{test_id}") # Clean up the save files

def test_transaction_logging(test_id: str) -> bool:
    dbg_info("--- Running Test: Transaction Logging ---")
    _setup_test_broker_manager(test_name=test_id)
    broker = BrokerManager()
    tx_log_path = broker.transaction_log_path
    try:
        broker.place_order(DEFAULT_BROKER_TEST_TICKER, OrderAction.BUY, 10, None)
        broker.place_order(DEFAULT_BROKER_TEST_TICKER, OrderAction.SELL, 5, None)
        
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
        BrokerManager.finalize()
        cleanup_test_broker_files(test_id)

def test_summarize_positions(test_id: str) -> bool:
    dbg_info("--- Running Test: Summarize Positions ---")
    _setup_test_broker_manager(test_name=test_id)
    broker_manager = BrokerManager()
    try:
        if not broker_manager.get_all_positions():
            broker_manager.place_order(DEFAULT_BROKER_TEST_TICKER, OrderAction.BUY, DEFAULT_BROKER_TEST_QTY, None)
        
        dbg_info("Calling summarize_positions(). Check output manually.")
        broker_manager.summarize_positions()
        return True
    except Exception as e:
        dbg_error(f"Error in test_summarize_positions: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        BrokerManager.finalize()
        cleanup_test_broker_files(test_id)

def test_summarize_transactions(test_id: str) -> bool:
    dbg_info("--- Running Test: Summarize Transactions ---")
    _setup_test_broker_manager(test_name=test_id)
    broker_manager = BrokerManager()
    try:
        if not broker_manager.get_transactions(): # Check if transactions already exist
             broker_manager.place_order(DEFAULT_BROKER_TEST_TICKER, OrderAction.BUY, 3, None)
             broker_manager.place_order(DEFAULT_BROKER_TEST_TICKER, OrderAction.SELL, 1, None)

        dbg_info("Calling summarize_transactions(). Check output manually.")
        broker_manager.summarize_transactions(duration=None)
        broker_manager.summarize_transactions(duration='month')
        return True
    except Exception as e:
        dbg_error(f"Error in test_summarize_transactions: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        BrokerManager.finalize()
        cleanup_test_broker_files(test_id)

def test_summarize_positions_no_positions(test_id="sum_pos_no_pos") -> bool:
    dbg_info("--- Running Test: Summarize Positions (No Positions) ---")
    _setup_test_broker_manager(test_name=test_id, initial_cash=100000.0, commission_rate=0.001)
    broker_manager = BrokerManager() # Ensure log is initialized if needed, and state is loaded (empty)
    try:
        # Ensure no positions are held (should be by default for a new broker)
        if broker_manager.get_all_positions():
            dbg_warning("Broker has existing positions, clearing for this test.")
            broker_manager.broker.positions = {}
            broker_manager.broker.cash = broker_manager.broker.initial_cash
            broker_manager.broker._save_state()

        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            broker_manager.summarize_positions()
        
        output = captured_output.getvalue()
        dbg_info(f"Captured output:\n{output}")

        if "No positions currently held." in output:
            dbg_info("Summarize positions correctly reported no positions.")
            return True
        else:
            dbg_error("Summarize positions did not report 'No positions currently held.' as expected.")
            return False
    except Exception as e:
        dbg_error(f"Error in test_summarize_positions_no_positions: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        BrokerManager.finalize()
        cleanup_test_broker_files(test_id)

def test_summarize_transactions_no_history(test_id="sum_tx_no_hist") -> bool:
    dbg_info("--- Running Test: Summarize Transactions (No History) ---")
    _setup_test_broker_manager(test_name=test_id, initial_cash=100000.0, commission_rate=0.001)
    broker_manager = BrokerManager() # Ensure log is initialized if needed, and state is loaded (empty)
    try:
        # Ensure transaction log is empty and no positions
        # _setup_test_broker_manager already cleans up files, and new broker has no positions.
        # So, just ensure no transactions are logged before calling summarize.
        
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            broker_manager.summarize_transactions(duration=None)
        
        output = captured_output.getvalue()
        dbg_info(f"Captured output:\n{output}")

        # Check for the specific output when no transactions are found
        if "Initial State (No Transactions)" in output or \
           "No transactions recorded and no positions held." in output:
            dbg_info("Summarize transactions correctly reported no history.")
            return True
        else:
            dbg_error("Summarize transactions did not report 'No transactions recorded and no positions held.' or 'Initial State (No Transactions)' as expected.")
            return False
    except Exception as e:
        dbg_error(f"Error in test_summarize_transactions_no_history: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        BrokerManager.finalize()
        cleanup_test_broker_files(test_id)

def test_summarize_transactions_with_pnl_and_duration(test_id="pnl_duration") -> bool:
    dbg_info("--- Running Test: Summarize Transactions (P/L and Duration) ---")
    # Set commission_rate to 0.0 as the mock will provide a fixed commission
    _setup_test_broker_manager(test_name=test_id, initial_cash=100000.0, commission_rate=0.0)
    broker_manager = BrokerManager() # Ensure log is initialized

    try:
        # Mock datetime.datetime.now() to control transaction timestamps
        # Mock get_last_price to control market prices for P/L calculation
        mock_market_prices = {
            "2330": 150.0, # Current price for unrealized P/L
            "MSFT": 200.0
        }

        # Create a MagicMock for the internal broker object
        # This mock_internal_broker is not directly used for patching broker_manager.broker
        # but rather for defining the side_effect for the patched place_order.
        # The actual patching happens in the `with patch.object` block below.
        mock_internal_broker_for_side_effect = MagicMock()
        mock_internal_broker_for_side_effect.get_last_price.side_effect = lambda s, price_type: mock_market_prices.get(s, 0.0)

        # Define a helper function for the mocked place_order side_effect
        # This function will simulate the MockBroker's behavior of calling the event_callback
        def _mock_broker_place_order_side_effect(symbol, action, qty, price=None):
            # Get the current mocked time
            current_mock_time = mock_dt.now() # Access the mocked datetime.now()

            # Determine fill price (use provided price or mocked market price)
            fill_price = price if price is not None else mock_internal_broker_for_side_effect.get_last_price(symbol, OrderPrice.LAST)
            commission = 0.005 # Fixed commission for this test

            # Create an OrderTracker to simulate a filled order
            order_tracker = OrderTracker(
                timestamp=current_mock_time,
                symbol=symbol,
                action=action,
                size=qty,
                price=fill_price,
                commission=commission,
                status=OrderStatus.FILLED,
            )
            
            # Manually call the BrokerManager's event_callback.
            # This is what MockBroker would do internally upon a successful fill.
            # This call will then trigger BrokerManager's _log_transaction.
            original_event_callback(Event.OrderFilled, order_tracker)

            # MockBroker.place_order (and thus BrokerManager.place_order) does not return anything for successful fills.
            # For failed orders, MockBroker.place_order returns None and triggers OrderFailed event.
            # For this test, we only simulate successful fills.
            return None # Explicitly return None as BrokerManager.place_order does not return anything.

        with patch('broker.brokermanager.datetime', wraps=datetime) as mock_dt, \
                patch.object(broker_manager.broker, 'get_last_price', side_effect=lambda s, price_type: mock_market_prices.get(s, 0.0)), \
                patch.object(broker_manager.broker, 'place_order', side_effect=_mock_broker_place_order_side_effect):
            
            # Set a fixed "current" time for the test
            test_current_time = datetime(2024, 5, 20, 10, 0, 0)
            mock_dt.now.return_value = test_current_time

            # Trade 1: Buy 2330 (60 days ago) - outside 'month' duration
            mock_dt.now.return_value = test_current_time - timedelta(days=60)
            broker_manager.place_order("2330", OrderAction.BUY, 10, 90.0)
            
            # Trade 2: Buy 2330 (15 days ago) - inside 'month' duration
            mock_dt.now.return_value = test_current_time - timedelta(days=15)
            broker_manager.place_order("2330", OrderAction.BUY, 5, 100.0)
            
            # Trade 3: Sell 2330 (5 days ago) - inside 'month' duration
            mock_dt.now.return_value = test_current_time - timedelta(days=5)
            broker_manager.place_order("2330", OrderAction.SELL, 7, 120.0)
            
            # Trade 4: Buy MSFT (2 days ago) - inside 'month' duration
            mock_dt.now.return_value = test_current_time - timedelta(days=2)
            broker_manager.place_order("MSFT", OrderAction.BUY, 2, 190.0)

            # Reset datetime.now() to current for summarize call
            mock_dt.now.return_value = test_current_time

            captured_output = io.StringIO()
            with contextlib.redirect_stdout(captured_output):
                broker_manager.summarize_transactions(duration='month')
            
            output = captured_output.getvalue()
            dbg_info(f"Captured output for 'month' duration:\n{output}")

            # Assertions for 'month' duration

            # Check overall summary
            lines = output.splitlines()
            
            found_period = False
            for line in lines:
                if "Period" in line and "Last month" in line:
                    found_period = True
                    break
            if not found_period:
                dbg_error("Summary period incorrect.")
                return False
            
            found_total_txns = False
            for line in lines:
                if "Total Txns" in line and "3" in line:
                    found_total_txns = True
                    break
            if not found_total_txns:
                dbg_error(f"Total transactions count incorrect. Expected 3, found: {output}")
                return False
            
            found_buys = False
            for line in lines:
                if "Buys" in line and "2" in line:
                    found_buys = True
                    break
            if not found_buys:
                dbg_error(f"Buy orders count incorrect. Expected 2, found: {output}")
                return False
            
            found_sells = False
            for line in lines:
                if "Sells" in line and "1" in line:
                    found_sells = True
                    break
            if not found_sells:
                dbg_error(f"Sell orders count incorrect. Expected 1, found: {output}")
                return False
            
            found_total_comm = False
            for line in lines:
                if "Total Comm." in line and "$0.01" in line: # 3 transactions * 0.005 commission = 0.015, rounded to 0.01
                    found_total_comm = True
                    break
            if not found_total_comm:
                dbg_error(f"Total commission incorrect. Expected $0.01, found: {output}")
                return False
            
            # Check Net P/L for the period (from Trade 3 sell)
            expected_net_pnl_str = "$186.66" # Rounded to 2 decimal places
            if expected_net_pnl_str not in output:
                dbg_error(f"Net P/L for period incorrect. Expected approx {expected_net_pnl_str}, found: {output}")
                return False

            # Check per-symbol details for 2330
            if "2330" in output and "$186.66" in output: # This is a weak check, but better than nothing
                dbg_info("Per-symbol P/L for 2330 seems present.")
            else:
                dbg_warning("Could not verify per-symbol P/L for 2330 precisely.")

            dbg_info("Summarize transactions with P/L and duration test successful.")
            return True

    except Exception as e:
        dbg_error(f"Error in test_summarize_transactions_with_pnl_and_duration: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        BrokerManager.finalize() # Ensure state is saved/cleaned up
        cleanup_test_broker_files(test_id)

def test_event_callback(test_id: str, symbol=DEFAULT_BROKER_TEST_TICKER, qty=DEFAULT_BROKER_TEST_QTY) -> bool:
    dbg_info(f"--- Running Test: Event Callback ({symbol}, {qty}) ---")
    _setup_test_broker_manager(test_name=test_id)
    broker_manager = BrokerManager()

    # Mock the event_callback method
    mock_callback = MagicMock()

    try:
        initial_cash = broker_manager.get_balance()
        
        # Use patch.object to temporarily replace the event_callback method
        with patch.object(broker_manager.order_svc, 'event_callback', new=mock_callback):
            # Place a buy order that should succeed
            broker_manager.place_order(symbol, OrderAction.BUY, qty, price=None)

            # Assert that the event_callback was called
            mock_callback.assert_called_once()
            
            # Get the arguments passed to the mock
            args, kwargs = mock_callback.call_args
            
            # Verify the event type
            if args[0] != Event.OrderFilled:
                dbg_error(f"Expected Event.OrderFilled, but got {args[0]}")
                return False
            
            # Verify the data is an OrderTracker instance
            order_tracker = args[1]
            if not isinstance(order_tracker, OrderTracker):
                dbg_error(f"Expected OrderTracker data, but got {type(order_tracker)}")
                return False
            
            # Verify key fields of the OrderTracker
            if order_tracker.symbol != symbol:
                dbg_error(f"OrderTracker symbol mismatch. Expected {symbol}, Got {order_tracker.symbol}")
                return False
            if order_tracker.action != OrderAction.BUY:
                dbg_error(f"OrderTracker action mismatch. Expected 'buy', Got {order_tracker.action}")
                return False
            if order_tracker.size != qty:
                dbg_error(f"OrderTracker size mismatch. Expected {qty}, Got {order_tracker.size}")
                return False
            if order_tracker.status != OrderStatus.FILLED:
                dbg_error(f"OrderTracker status mismatch. Expected 'FILLED', Got {order_tracker.status}")
                return False

        dbg_info(f"Event callback successfully triggered and verified for OrderFilled event.")
        return True
    except Exception as e:
        dbg_error(f"Error in test_event_callback: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        BrokerManager.finalize()
        cleanup_test_broker_files(test_id)

# --- Test Runner ---
def run_broker_tests(test_names: list[str]):
    results = {}
    
    # All tests are now standalone
    all_test_definitions = {
        "initial_state": test_initial_state,
        "buy_sufficient_cash": test_place_buy_order_sufficient_cash,
        "get_position": test_get_position, # Renamed and made standalone
        "sell_sufficient_position": test_place_sell_order_sufficient_position,
        "buy_insufficient_cash": test_place_buy_order_insufficient_cash,
        "sell_insufficient_position": test_place_sell_order_insufficient_position,
        "portfolio_value": test_portfolio_value,
        "summarize_positions": test_summarize_positions,
        "summarize_transactions": test_summarize_transactions,
        "save_load_state": test_save_load_state,
        "transaction_logging": test_transaction_logging,
        "summarize_positions_no_positions": test_summarize_positions_no_positions,
        "summarize_transactions_no_history": test_summarize_transactions_no_history,
        "summarize_transactions_pnl_duration": test_summarize_transactions_with_pnl_and_duration,
        "event_callback": test_event_callback, # New test case
    }

    tests_to_run_names = []
    if "all" in test_names:
        tests_to_run_names = list(all_test_definitions.keys())
    else:
        tests_to_run_names = [name for name in test_names if name in all_test_definitions]

    if not tests_to_run_names:
        dbg_warning(f"No valid broker tests specified or found in: {test_names}")
        return

    dbg_info("=== Starting Broker Tests ===")
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

    # Cleanup of individual test files is handled within each test function's finally block.
    # This block cleans up the main test directories if they become empty.
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
        status_str = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        dbg_info(f"  {name:<30}: {status_str}")
    total_failed = len(tests_to_run_names) - total_passed
    passed_str = f"{GREEN}Passed: {total_passed}{RESET}"
    failed_str = f"{RED}Failed: {total_failed}{RESET}" if total_failed > 0 else f"Failed: {total_failed}"
    dbg_info(f"Total Tests Run: {len(tests_to_run_names)}, {passed_str}, {failed_str}")
    dbg_info("==========================")
    return {"total": len(tests_to_run_names), "passed": total_passed, "failed": total_failed}

