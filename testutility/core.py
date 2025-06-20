# testutility/core.py
import os
import shutil
import traceback
import io
import contextlib
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, call
import threading
import time # For actual short sleeps if needed, but mostly mocked

# Local file
from core.core import Core, TradingStatus, sleep_with_flag, sleep_until_with_flag
from market.market import MarketTime
from utility.debug import dbg_info, dbg_warning, dbg_error, dbg_trace

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

# Helper to create a unique test ID
def _get_test_id(test_name: str) -> str:
    return f"{test_name}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

# --- Individual Test Cases ---

def test_core_initialization(test_id: str) -> bool:
    dbg_info(f"--- Running Test: {test_id} - Core Initialization ---")
    core_instance = None
    try:
        core_instance = Core()
        core_instance.initialize()

        if not isinstance(core_instance, Core):
            dbg_error("Core instance not created correctly.")
            return False
        if core_instance.flag_core_running:
            dbg_error("flag_core_running should be False initially.")
            return False
        if core_instance.flag_heatbeat_running:
            dbg_error("flag_heatbeat_running should be False initially.")
            return False
        if core_instance.flag_trade_service_running:
            dbg_error("flag_trade_service_running should be False initially.")
            return False
        if core_instance.flag_selling_service_running:
            dbg_error("flag_selling_service_running should be False initially.")
            return False
        if not isinstance(core_instance.trading_status, TradingStatus):
            dbg_error("trading_status not initialized correctly.")
            return False
        
        dbg_info("Core initialization test passed.")
        return True
    except Exception as e:
        dbg_error(f"Error in {test_id}: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        # No specific cleanup needed for just initialization
        core_instance.finalize()

def test_core_start_and_stop_flow(test_id: str) -> bool:
    dbg_info(f"--- Running Test: {test_id} - Core Start/Stop Flow ---")
    core_instance = Core()
    core_instance.initialize()
    
    # Mock sleep functions to prevent actual blocking
    with patch('core.core.sleep_with_flag', side_effect=lambda *args, **kwargs: (time.sleep(5) or -1)) as mock_sleep_with_flag, \
         patch('core.core.sleep_until_with_flag', side_effect=lambda *args, **kwargs: (time.sleep(5) or -1)) as mock_sleep_until_with_flag, \
         patch.object(core_instance, '_Core__update_datasource', return_value=True) as mock_update_datasource, \
         patch.object(core_instance.trading, 'trading_eval', return_value=[]) as mock_trading_eval, \
         patch.object(core_instance.trading, 'buying_exec', return_value=True) as mock_buying_exec, \
         patch.object(core_instance.trading, 'selling_eval', return_value=[]) as mock_selling_eval, \
         patch.object(core_instance.trading, 'selling_exec', return_value=True) as mock_selling_exec, \
         patch.object(core_instance.tdcli, 'run') as mock_tdcli_run: # Mock CLI run to prevent blocking
        try:
            
            # Start core in a separate thread to allow main thread to interact
            core_thread = threading.Thread(target=core_instance.start)
            core_thread.start()

            # Wait briefly for services to start and set their flags
            # A small actual sleep is necessary here, as the flags are set by the threads themselves.
            start_time = time.time()
            timeout = 5 # seconds
            dbg_info(f"start time: {start_time}")
            while (not core_instance.flag_heatbeat_running or
                   not core_instance.flag_trade_service_running or
                   not core_instance.flag_selling_service_running or
                   not core_instance.flag_datasource_service_running) and (time.time() - start_time < timeout):
                time.sleep(0.1) # Small sleep to yield to other threads
            dbg_info(f"end time: {time.time()}")

            if not core_instance.flag_core_running:
                dbg_error("flag_core_running is False after start.")
                return False
            if not core_instance.flag_heatbeat_running:
                dbg_error("flag_heatbeat_running is False after start.")
                return False
            if not core_instance.flag_trade_service_running:
                dbg_error("flag_trade_service_running is False after start.")
                return False
            if not core_instance.flag_selling_service_running:
                dbg_error("flag_selling_service_running is False after start.")
                return False
            if not core_instance.flag_datasource_service_running:
                dbg_error("flag_datasource_service_running is False after start.")
                return False

            dbg_info("All service flags are True after start.")
            # wait for start cli & heartbeat.
            time.sleep(3)

            # Signal core to stop
            core_instance.stop() # This sets flag_core_running to False and stop_event.set()
            
            # Wait for the core thread to finish
            core_thread.join(timeout=5) # Give it some time to shut down
            if core_thread.is_alive():
                dbg_error("Core thread did not terminate within timeout.")
                return False

            # Verify flags are False after stopping
            if core_instance.flag_core_running:
                dbg_error("flag_core_running is True after quit.")
                return False
            if core_instance.flag_heatbeat_running:
                dbg_error("flag_heatbeat_running is True after quit.")
                return False
            if core_instance.flag_trade_service_running:
                dbg_error("flag_trade_service_running is True after quit.")
                return False
            if core_instance.flag_selling_service_running:
                dbg_error("flag_selling_service_running is True after quit.")
                return False
            if core_instance.flag_datasource_service_running:
                dbg_error("flag_datasource_service_running is True after quit.")
                return False

            dbg_info("Core start/stop flow test passed.")
            return True
        except Exception as e:
            dbg_error(f"Error in {test_id}: {e}")
            dbg_error(traceback.format_exc())
            return False
        finally:
            # Ensure the thread is joined even if test fails early
            if 'core_thread' in locals() and core_thread.is_alive():
                core_instance.stop() # Attempt to stop again
                core_thread.join(timeout=1)
            # No specific file cleanup for this test
            core_instance.finalize() # Attempt to stop again

def test_core_sanity_check_method(test_id: str) -> bool:
    dbg_info(f"--- Running Test: {test_id} - Sanity Check Method ---")
    core_instance = Core()
    try:
        # Test 1: All flags False (initial state)
        result = core_instance._Core__sanitycheck()
        if result:
            dbg_error("Sanity check should fail when no services are running.")
            return False
        
        # Test 2: All flags True
        core_instance.flag_core_running = True
        core_instance.flag_heatbeat_running = True
        core_instance.flag_trade_service_running = True
        core_instance.flag_selling_service_running = True
        core_instance.flag_datasource_service_running = True
        result = core_instance._Core__sanitycheck()
        if not result:
            dbg_error("Sanity check should pass when all services are running.")
            return False

        # Test 3: One flag False (e.g., heartbeat)
        core_instance.flag_heatbeat_running = False
        result = core_instance._Core__sanitycheck()
        if result:
            dbg_error("Sanity check should fail when heartbeat is down.")
            return False
        
        # Reset for next test
        core_instance.flag_heatbeat_running = True
        core_instance.flag_trade_service_running = False
        result = core_instance._Core__sanitycheck()
        if result:
            dbg_error("Sanity check should fail when trading service is down.")
            return False

        dbg_info("Sanity check method test passed.")
        return True
    except Exception as e:
        dbg_error(f"Error in {test_id}: {e}")
        dbg_error(traceback.format_exc())
        return False

def test_cmd_status_output(test_id: str) -> bool:
    dbg_info(f"--- Running Test: {test_id} - cmd_status Output ---")
    core_instance = Core()
    core_instance.initialize() # Initialize to set up market, trading, etc.
    
    # Set some flags to simulate a running state
    core_instance.flag_core_running = True
    core_instance.flag_heatbeat_running = True
    core_instance.flag_trade_service_running = True
    core_instance.flag_selling_service_running = True
    core_instance.flag_datasource_service_running = True

    # Set mock wakeup times
    mock_now = datetime(2024, 6, 8, 10, 0, 0)
    core_instance.trading_status.Datasource.next_wakeup_time = mock_now + timedelta(hours=1)
    core_instance.trading_status.Trading.next_wakeup_time = mock_now + timedelta(hours=2)
    core_instance.trading_status.Selling.next_wakeup_time = mock_now + timedelta(minutes=30)
    
    # Simulate a target buying list
    core_instance.trading_status.Trading.target_buying_list = ['2330', '2454']
    
    # Mock market.get_data_info to provide consistent data
    mock_market_data = {
        '2330': {'code': '2330', 'name': 'TSMC', 'type': 'Stock', 'market': 'TWSE', 'category': 'Semiconductor', 'start': '1994-09-05', 'country': 'Taiwan'},
        '2454': {'code': '2454', 'name': 'MediaTek', 'type': 'Stock', 'market': 'TWSE', 'category': 'IC Design', 'start': '2001-07-23', 'country': 'Taiwan'}
    }
    try:
        with patch.object(core_instance.market, 'get_data_info', side_effect=lambda x: mock_market_data.get(x)), \
            patch('core.core.datetime') as mock_dt: # Mock datetime for sanity check
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw) # Allow datetime.datetime() calls

            captured_output = io.StringIO()
            with contextlib.redirect_stdout(captured_output):
                core_instance.cmd_status()
            
            output = captured_output.getvalue()
            dbg_info(f"Captured output:\n{output}")

            # Assertions for key phrases in the output
            if "Core Running               : True" not in output:
                dbg_error("Core Running status incorrect.")
                return False
            if "Heartbeat Service Running  : True" not in output:
                dbg_error("Heartbeat Service Running status incorrect.")
                return False
            if "Datasource Service Running : True (Next wake up-> 2024-06-08 11:00:00)" not in output:
                dbg_error("Datasource Service Running status or wakeup time incorrect.")
                return False
            if "Trading Service Running    : True (Next wake up-> 2024-06-08 12:00:00)" not in output:
                dbg_error("Trading Service Running status or wakeup time incorrect.")
                return False
            if "Selling Service Running    : True (Next wake up-> 2024-06-08 10:30:00)" not in output:
                dbg_error("Selling Service Running status or wakeup time incorrect.")
                return False
            if "Sanity Check: True" not in output:
                dbg_error("Sanity Check status incorrect.")
                return False
            if "Target Buying List:" not in output:
                dbg_error("Target Buying List header missing.")
                return False
            if "2330" not in output or "TSMC" not in output:
                dbg_error("2330 (TSMC) not found in buying list table.")
                return False
            if "2454" not in output or "MediaTek" not in output:
                dbg_error("2454 (MediaTek) not found in buying list table.")
                return False

            dbg_info("cmd_status output test passed.")
            return True
    except Exception as e:
        dbg_error(f"Error in {test_id}: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        # Reset flags for other tests if this instance is reused (though it shouldn't be)
        core_instance.flag_core_running = False
        core_instance.flag_heatbeat_running = False
        core_instance.flag_trade_service_running = False
        core_instance.flag_selling_service_running = False
        core_instance.flag_datasource_service_running = False
        core_instance.finalize()

def test_datasource_service_loop_and_update(test_id: str) -> bool:
    dbg_info(f"--- Running Test: {test_id} - Datasource Service Loop ---")
    core_instance = Core()
    core_instance.initialize()
    
    # Mock datetime.now() and MarketTime methods to control time progression
    mock_now = datetime(2024, 6, 8, 15, 0, 0) # After market update time
    
    try:
        with patch('core.core.datetime') as mock_dt, \
            patch('market.market.MarketTime.get_next_market_update_time', return_value=mock_now + timedelta(days=1, hours=1)) as mock_get_next_update_time, \
            patch('core.core.sleep_until_with_flag', side_effect=[None, -1]) as mock_sleep_until_with_flag, \
            patch.object(core_instance, '_Core__update_datasource', return_value=True) as mock_update_datasource:
            
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw) # Allow datetime.datetime() calls

            core_instance.flag_core_running = True # Manually set core running flag for service to run

            datasource_thread = threading.Thread(target=core_instance._Core__datasource_service)
            datasource_thread.start()

            # Wait for the service to run at least once and then stop
            start_time = time.time()
            timeout = 5 # seconds
            while not mock_update_datasource.called and (time.time() - start_time < timeout):
                time.sleep(0.1)

            if not mock_update_datasource.called:
                dbg_error("Datasource update was not called.")
                return False
            
            # Verify that sleep_until_with_flag was called with the correct target time
            mock_sleep_until_with_flag.assert_called_once_with(mock_get_next_update_time.return_value, core_instance.stop_event)

            # Verify that the next_wakeup_time was set and then reset
            if core_instance.trading_status.Datasource.next_wakeup_time is not None:
                dbg_error(f"Datasource next_wakeup_time not reset to None: {core_instance.trading_status.Datasource.next_wakeup_time}")
                return False

            # Signal stop and join thread
            core_instance.flag_datasource_service_running = False # This will cause the loop to exit
            datasource_thread.join(timeout=1)
            if datasource_thread.is_alive():
                dbg_error("Datasource service thread did not terminate.")
                return False

            dbg_info("Datasource service loop test passed.")
            return True
    except Exception as e:
        dbg_error(f"Error in {test_id}: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        # Ensure flags are reset
        core_instance.flag_core_running = False
        core_instance.flag_datasource_service_running = False
        core_instance.finalize()

def test_trading_service_flow(test_id: str) -> bool:
    dbg_info(f"--- Running Test: {test_id} - Trading Service Flow ---")
    core_instance = Core()
    core_instance.initialize()
    
    mock_now = datetime(2024, 6, 8, 10, 0, 0) # During market hours
    mock_market_open = datetime(2024, 6, 8, 9, 0, 0)
    mock_market_update = datetime(2024, 6, 8, 14, 30, 0)

    try:
        with patch('core.core.datetime') as mock_dt, \
            patch('market.market.MarketTime.get_next_market_open_time', return_value=mock_market_open) as mock_get_next_market_open_time, \
            patch('market.market.MarketTime.get_next_market_update_time', return_value=mock_market_update) as mock_get_next_market_update_time, \
            patch('market.market.MarketTime.is_trading_day', return_value=True) as mock_is_trading_day, \
            patch('core.core.sleep_until_with_flag', side_effect=[None, None, -1]) as mock_sleep_until_with_flag, \
            patch.object(core_instance.trading, 'trading_eval', return_value=['2330']) as mock_trading_eval, \
            patch.object(core_instance.trading, 'buying_exec', return_value=True) as mock_buying_exec:
            
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            core_instance.flag_core_running = True

            trading_thread = threading.Thread(target=core_instance._Core__trading_service)
            trading_thread.start()

            # Wait for trading_eval to be called
            start_time = time.time()
            timeout = 5
            while not mock_trading_eval.called and (time.time() - start_time < timeout):
                time.sleep(0.1)

            if not mock_trading_eval.called:
                dbg_error("trading_eval was not called.")
                return False
            
            # Verify buying_exec was called with the returned list
            start_time = time.time()
            while not mock_buying_exec.called and (time.time() - start_time < timeout):
                time.sleep(0.1)

            if not mock_buying_exec.called:
                dbg_error("buying_exec was not called.")
                return False
            
            mock_buying_exec.assert_called_once_with(['2330'])

            # Verify sleep calls and wakeup times
            # First sleep: for evaluation
            expected_eval_wakeup = mock_market_update + timedelta(hours=1) # Based on current_time > MarketTime.MARKET_OPEN_TIME
            mock_sleep_until_with_flag.assert_has_calls([
                call(expected_eval_wakeup, core_instance.stop_event),
                call(mock_market_open.replace(hour=9, minute=0, second=0, microsecond=0), core_instance.stop_event)
            ])

            if core_instance.trading_status.Trading.next_wakeup_time is not None:
                dbg_error(f"Trading next_wakeup_time not reset to None: {core_instance.trading_status.Trading.next_wakeup_time}")
                return False

            # Signal stop and join thread
            core_instance.flag_trade_service_running = False
            trading_thread.join(timeout=1)
            if trading_thread.is_alive():
                dbg_error("Trading service thread did not terminate.")
                return False

            dbg_info("Trading service flow test passed.")
            return True
    except Exception as e:
        dbg_error(f"Error in {test_id}: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        core_instance.flag_core_running = False
        core_instance.flag_trade_service_running = False
        core_instance.finalize()

def test_selling_service_flow(test_id: str) -> bool:
    dbg_info(f"--- Running Test: {test_id} - Selling Service Flow ---")
    core_instance = Core()
    core_instance.initialize()
    
    mock_now = datetime(2024, 6, 8, 10, 0, 0) # During market hours
    mock_market_open = datetime(2024, 6, 8, 9, 0, 0)
    mock_market_close = datetime(2024, 6, 8, 13, 20, 0) # Adjusted for test

    try:
        with patch('core.core.datetime') as mock_dt, \
            patch('market.market.MarketTime.get_next_market_open_time', return_value=mock_market_open) as mock_get_next_market_open_time, \
            patch('market.market.MarketTime.get_next_market_close_time', return_value=mock_market_close) as mock_get_next_market_close_time, \
            patch('core.core.sleep_with_flag', side_effect=lambda *args, **kwargs: (time.sleep(1) or -1)) as mock_sleep_with_flag, \
            patch('core.core.sleep_until_with_flag', side_effect=lambda *args, **kwargs: (time.sleep(1) or -1)) as mock_sleep_until_with_flag, \
            patch.object(core_instance.trading, 'selling_eval', return_value=['2454']) as mock_selling_eval, \
            patch.object(core_instance.trading, 'selling_exec', return_value=True) as mock_selling_exec:
            
            mock_dt.now.return_value = mock_now
            mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

            core_instance.flag_core_running = True

            selling_thread = threading.Thread(target=core_instance._Core__selling_service)
            selling_thread.start()

            # Wait for selling_eval to be called at least once
            start_time = time.time()
            timeout = 5
            while not mock_selling_eval.called and (time.time() - start_time < timeout):
                time.sleep(0.1)

            if not mock_selling_eval.called:
                dbg_error("selling_eval was not called.")
                return False
            
            # Verify selling_exec was called if selling_eval returned items
            start_time = time.time()
            while not mock_selling_exec.called and (time.time() - start_time < timeout):
                time.sleep(0.1)

            if not mock_selling_exec.called:
                dbg_error("selling_exec was not called.")
                return False
            
            mock_selling_exec.assert_called_once_with(['2454'])

            # wait for the sleep ends.
            time.sleep(3)
            # Verify sleep calls
            # First sleep: intra-day monitoring (mock_sleep_with_flag)
            # Second sleep: until next market open (mock_sleep_until_with_flag)
            mock_sleep_with_flag.assert_called_once() # Should be called for intra-day sleep
            mock_sleep_until_with_flag.assert_called_once_with(mock_market_open.replace(hour=9, minute=0, second=0, microsecond=0), core_instance.stop_event)

            if core_instance.trading_status.Selling.next_wakeup_time is not None:
                dbg_error(f"Selling next_wakeup_time not reset to None: {core_instance.trading_status.Selling.next_wakeup_time}")
                return False

            # Signal stop and join thread
            core_instance.flag_selling_service_running = False
            selling_thread.join(timeout=1)
            if selling_thread.is_alive():
                dbg_error("Selling service thread did not terminate.")
                return False

            dbg_info("Selling service flow test passed.")
            return True
    except Exception as e:
        dbg_error(f"Error in {test_id}: {e}")
        dbg_error(traceback.format_exc())
        return False
    finally:
        core_instance.flag_core_running = False
        core_instance.flag_selling_service_running = False
        core_instance.finalize()

# --- Test Runner ---
def run_core_tests(test_names: list[str]):
    results = {}
    
    all_test_definitions = {
        "initialization": test_core_initialization,
        "start_stop_flow": test_core_start_and_stop_flow,
        "sanity_check_method": test_core_sanity_check_method,
        "cmd_status_output": test_cmd_status_output,
        "datasource_service_loop": test_datasource_service_loop_and_update,
        "trading_service_flow": test_trading_service_flow,
        "selling_service_flow": test_selling_service_flow,
    }

    tests_to_run_names = []
    if "all" in test_names:
        tests_to_run_names = list(all_test_definitions.keys())
    else:
        tests_to_run_names = [name for name in test_names if name in all_test_definitions]

    if not tests_to_run_names:
        dbg_warning(f"No valid core tests specified or found in: {test_names}")
        return {"total": 0, "passed": 0, "failed": 0}

    dbg_info("=== Starting Core Tests ===")
    total_passed = 0
    for name in tests_to_run_names:
        dbg_trace(f"Executing test: {name}")
        test_id = _get_test_id(name) # Generate unique ID for each test run
        try:
            test_func = all_test_definitions[name]
            result = test_func(test_id)
            
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

    dbg_info("=== Core Tests Summary ===")
    for name, result in results.items():
        status_str = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        dbg_info(f"  {name:<30}: {status_str}")
    total_failed = len(tests_to_run_names) - total_passed
    passed_str = f"{GREEN}Passed: {total_passed}{RESET}"
    failed_str = f"{RED}Failed: {total_failed}{RESET}" if total_failed > 0 else f"Failed: {total_failed}"
    dbg_info(f"Total Tests Run: {len(tests_to_run_names)}, {passed_str}, {failed_str}")
    dbg_info("==========================")
    return {"total": len(tests_to_run_names), "passed": total_passed, "failed": total_failed}

