# system file
import traceback
import time

# Local file
from core.config import *
from utility.debug import *
from utility.cli import CommandLineInterface
from market.market import Market # Import Market class
from testutility.market import run_market_tests # Import the test runner
from testutility.broker import run_broker_tests # Import the broker test runner
from testutility.backtest import run_backtest_tests # Import the backtest test runner
from testutility.core import run_core_tests # Import the core test runner
from testutility.integration import run_integration_tests # Import the integration test runner
from trading.evaluate import Evaluate # Import Evaluate class
from trading.trading import Trading # Import Trading class
from testutility.trading import run_trading_tests # Import the trading test runner
import traceback # For detailed error logging in cmd_market
from tabulate import tabulate # For pretty table output

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
RESET = "\033[0m"

class TestCLI(CommandLineInterface):
    def __init__(self):
        super().__init__(promote='test') # Initialize parent CLI
        self.market = Market() # Instantiate Market for testing
        # self.evaluate_instance = Evaluate(development = True) # Instantiate Evaluate for testing
        # self.trading_instance = Trading() # Instantiate Trading for testing
        # For testing purposes, we often want to use controlled/smaller datasets
        # or specific test paths within the Evaluate class.
        # Setting flag_development to True can enable this if Evaluate is designed accordingly.
        # self.evaluate_instance.flag_development = True
        # dbg_info(f"TestCLI: Evaluate instance created with flag_development={self.evaluate_instance.flag_development}")
        # if self.evaluate_instance.flag_development:
        #     dbg_info(f"  Evaluate test_buy_list: {self.evaluate_instance.test_buy_list}")
        #     dbg_info(f"  Evaluate test_sell_list: {self.evaluate_instance.test_sell_list}")

        self._register_test_commands()

    def _register_test_commands(self):
        """Registers all test commands."""
        # Define available core sub-tests
        self.core_sub_tests = [
            "initialization",
            "start_stop_flow",
            "sanity_check_method",
            "cmd_status_output",
            "datasource_service_loop",
            "trading_service_flow",
            "selling_service_flow",
            "all" # Special command to run all tests
        ]
        self.regist_cmd(
            "core",
            self.cmd_core,
            description=f"Run tests for core.py. Sub-tests: {', '.join(self.core_sub_tests)}",
            arg_list=self.core_sub_tests,
            group='testing'
        )

        # Define available market sub-tests
        self.market_sub_tests = [
            "list_providers",
            "switch_market",
            "get_data_list",
            "get_data",
            "get_info",
            "get_top_product_list", # New test case
            "get_product_list_by_date", # New test case
            "update_data", # New test case
            "all" # Special command to run all tests
        ]
        self.regist_cmd(
            "market",
            self.cmd_market,
            description=f"Run tests for market.py. Sub-tests: {', '.join(self.market_sub_tests)}",
            arg_list=self.market_sub_tests,
            group='testing'
        )

        # Define available trading sub-tests
        self.trading_sub_tests = [
            "eval_buying",       # Was buying_evaluation, tests Evaluate.buying_evaluation
            "eval_selling",      # Was selling_evaluation, tests Evaluate.selling_evaluation
            "exec_buying",       # Tests Trading.buying_exec
            "exec_selling",      # Tests Trading.selling_exec
            "flow_trading_eval", # Tests Trading.trading_eval flow
            "flow_selling_eval", # Tests Trading.selling_eval flow
            "all"                # Special command to run all trading related tests
        ]
        self.regist_cmd(
            "trading",
            self.cmd_trading,
            description=f"Run tests for trading (Evaluate & Trading classes). Sub-tests: {', '.join(self.trading_sub_tests)}",
            arg_list=self.trading_sub_tests,
            group='testing'
        )

        # Define available broker sub-tests (match keys in run_broker_tests)
        self.broker_sub_tests = [
            "initial_state",
            "buy_sufficient_cash",
            "get_position",
            "sell_sufficient_position",
            "buy_insufficient_cash",
            "sell_insufficient_position",
            "portfolio_value",
            "summarize_positions",
            "summarize_transactions",
            "summarize_positions_no_positions",
            "summarize_transactions_no_history",
            "summarize_transactions_pnl_duration",
            "save_load_state",
            "transaction_logging",
            "event_callback",
            "all" # Special command
        ]
        self.regist_cmd(
            "broker",
            self.cmd_broker,
            description=f"Run tests for BrokerManager/BaseBroker. Sub-tests: {', '.join(self.broker_sub_tests)}",
            arg_list=self.broker_sub_tests,
            group='testing'
        )

        # Define available backtest sub-tests (match keys in run_backtest_tests)
        self.backtest_sub_tests = [
            "initial_configuration",
            "setup_method",
            "add_symbol",
            "add_data_frame",
            "add_history_validation",
            "add_strategy",
            "add_optstrategy",
            "eval_basic",
            "eval_with_history",
            "save_report",
            "show_result",
            "eval_lock",
            "all" # Special command
        ]
        self.regist_cmd(
            "backtest",
            self.cmd_backtest,
            description=f"Run tests for backtest.py. Sub-tests: {', '.join(self.backtest_sub_tests)}",
            arg_list=self.backtest_sub_tests,
            group='testing'
        )

        # Define available integration sub-tests (match keys in run_integration_tests)
        self.integration_sub_tests = [
            "buying_flow",
            "selling_flow",
            "all" # Special command to run all tests
        ]
        self.regist_cmd(
            "integration",
            self.cmd_integration,
            description=f"Run tests for integration. Sub-tests: {', '.join(self.integration_sub_tests)}",
            arg_list=self.integration_sub_tests,
            group='testing'
        )

        # Define top-level test groups
        self.test_groups = ["market", "broker", "trading", "backtest", "core", "integration", "all"]
        self.regist_cmd(
            "test",
            self.cmd_test,
            description=f"Run specified test groups or all tests (default). Groups: {', '.join(g for g in self.test_groups if g != 'all')}",
            arg_list=self.test_groups,
            group='testing' # Group for the master test command
        )
        # Add other command registrations if needed

    def cmd_core(self, args):
        """Command handler for 'core' tests."""
        if args['#'] == 0:
            dbg_error("Please specify a core sub-test or 'all'.")
            dbg_info(f"Available sub-tests: {', '.join(self.core_sub_tests)}")
            return False

        tests_to_run = []
        for i in range(1, args['#'] + 1):
            sub_cmd = args[str(i)]
            if sub_cmd in self.core_sub_tests:
                tests_to_run.append(sub_cmd)
            else:
                self.print_warning(f"Unknown core sub-test '{sub_cmd}', ignoring.")

        if not tests_to_run:
            dbg_error("No valid core sub-tests specified.")
            return False

        if "all" in tests_to_run:
            tests_to_run = ["all"]

        dbg_info(f"Running core tests: {', '.join(tests_to_run)}")
        try:
            run_core_tests(tests_to_run)
            return True # Command execution success (tests pass/fail internally)
        except Exception as e:
            dbg_error(f"An error occurred while running core tests: {e}")
            dbg_error(traceback.format_exc())
            return False # Command execution failure

    def cmd_market(self, args):
        """Command handler for 'market' tests."""
        if args['#'] == 0:
            dbg_error("Please specify a market sub-test or 'all'.")
            dbg_info(f"Available sub-tests: {', '.join(self.market_sub_tests)}")
            return False

        # Collect all specified sub-tests
        tests_to_run = []
        for i in range(1, args['#'] + 1):
            sub_cmd = args[str(i)]
            if sub_cmd in self.market_sub_tests:
                tests_to_run.append(sub_cmd)
            else:
                self.print_warning(f"Unknown market sub-test '{sub_cmd}', ignoring.")

        if not tests_to_run:
            dbg_error("No valid market sub-tests specified.")
            return False

        # If 'all' is specified, it overrides others for simplicity in the runner
        if "all" in tests_to_run:
            tests_to_run = ["all"]

        dbg_info(f"Running market tests: {', '.join(tests_to_run)}")
        try:
            # Call the test runner function from testutility.market
            run_market_tests(self.market, tests_to_run)
            return True # Indicate command execution success (tests may pass/fail internally)
        except Exception as e:
            dbg_error(f"An error occurred while running market tests: {e}")
            dbg_error(traceback.format_exc())
            return False # Indicate command execution failure

    def cmd_trading(self, args):
        """Command handler for 'trading' tests."""
        if args['#'] == 0:
            dbg_error("Please specify a trading sub-test or 'all'.")
            dbg_info(f"Available sub-tests: {', '.join(self.trading_sub_tests)}")
            return False

        tests_to_run = []
        for i in range(1, args['#'] + 1):
            sub_cmd = args[str(i)]
            if sub_cmd in self.trading_sub_tests:
                tests_to_run.append(sub_cmd)
            else:
                self.print_warning(f"Unknown trading sub-test '{sub_cmd}', ignoring.")

        if not tests_to_run:
            dbg_error("No valid trading sub-tests specified.")
            return False

        if "all" in tests_to_run:
            tests_to_run = ["all"]

        dbg_info(f"Running trading tests: {', '.join(tests_to_run)}")
        try:
            # Ensure evaluate_instance.flag_development is True for test runs
            # This is now set in __init__, but can be double-checked or set here if needed per-run
            # self.evaluate_instance.flag_development = True

            # Pass both instances; run_trading_tests will determine which to use for each specific test
            run_trading_tests(tests_to_run)
            return True # Command execution success (tests pass/fail internally)
        except Exception as e:
            dbg_error(f"An error occurred while running trading tests: {e}")
            dbg_error(traceback.format_exc())
            return False # Command execution failure

    def cmd_broker(self, args):
        """Command handler for 'broker' tests."""
        if args['#'] == 0:
            dbg_error("Please specify a broker sub-test or 'all'.")
            dbg_info(f"Available sub-tests: {', '.join(self.broker_sub_tests)}")
            return False

        # Collect all specified sub-tests
        tests_to_run = []
        for i in range(1, args['#'] + 1):
            sub_cmd = args[str(i)]
            if sub_cmd in self.broker_sub_tests:
                tests_to_run.append(sub_cmd)
            else:
                dbg_warning(f"Unknown broker sub-test '{sub_cmd}', ignoring.") # Use dbg_warning

        if not tests_to_run:
            dbg_error("No valid broker sub-tests specified.")
            return False

        # If 'all' is specified, it overrides others
        if "all" in tests_to_run:
            tests_to_run = ["all"]

        dbg_info(f"Running broker tests: {', '.join(tests_to_run)}")
        try:
            # Call the test runner function from testutility.broker
            run_broker_tests(tests_to_run)
            return True # Indicate command execution success
        except Exception as e:
            dbg_error(f"An error occurred while running broker tests: {e}")
            dbg_error(traceback.format_exc())
            return False # Indicate command execution failure

    def cmd_backtest(self, args):
        """Command handler for 'backtest' tests."""
        if args['#'] == 0:
            dbg_error("Please specify a backtest sub-test or 'all'.")
            dbg_info(f"Available sub-tests: {', '.join(self.backtest_sub_tests)}")
            return False

        tests_to_run = []
        for i in range(1, args['#'] + 1):
            sub_cmd = args[str(i)]
            if sub_cmd in self.backtest_sub_tests:
                tests_to_run.append(sub_cmd)
            else:
                self.print_warning(f"Unknown backtest sub-test '{sub_cmd}', ignoring.")

        if not tests_to_run:
            dbg_error("No valid backtest sub-tests specified.")
            return False

        if "all" in tests_to_run:
            tests_to_run = ["all"]

        dbg_info(f"Running backtest tests: {', '.join(tests_to_run)}")
        try:
            run_backtest_tests(tests_to_run)
            return True # Command execution success (tests pass/fail internally)
        except Exception as e:
            dbg_error(f"An error occurred while running backtest tests: {e}")
            dbg_error(traceback.format_exc())
            return False # Command execution failure

    def cmd_integration(self, args):
        """Command handler for 'integration' tests."""
        if args['#'] == 0:
            dbg_error("Please specify an integration sub-test or 'all'.")
            dbg_info(f"Available sub-tests: {', '.join(self.integration_sub_tests)}")
            return False

        tests_to_run = []
        for i in range(1, args['#'] + 1):
            sub_cmd = args[str(i)]
            if sub_cmd in self.integration_sub_tests:
                tests_to_run.append(sub_cmd)
            else:
                self.print_warning(f"Unknown integration sub-test '{sub_cmd}', ignoring.")

        if not tests_to_run:
            dbg_error("No valid integration sub-tests specified.")
            return False

        if "all" in tests_to_run:
            tests_to_run = ["all"]

        dbg_info(f"Running integration tests: {', '.join(tests_to_run)}")
        try:
            run_integration_tests(tests_to_run)
            return True # Command execution success (tests pass/fail internally)
        except Exception as e:
            dbg_error(f"An error occurred while running integration tests: {e}")
            dbg_error(traceback.format_exc())
            return False # Command execution failure

    def cmd_test(self, args):
        """Command handler for running all or specified test groups."""
        run_all_tests = False
        requested_groups = []

        if args['#'] == 0:
            dbg_info("No arguments provided to 'test', running all test groups by default.")
            run_all_tests = True
        else:
            requested_groups = [args[str(i)] for i in range(1, args['#'] + 1)]
            run_all_tests = "all" in requested_groups

        # Validate requested groups if not running all
        if not run_all_tests:
            valid_groups = [group for group in requested_groups if group in self.test_groups and group != "all"]
            if not valid_groups:
                valid_group_names = [g for g in self.test_groups if g != 'all']
                dbg_error(f"No valid test groups specified in: {requested_groups}. Available: {', '.join(valid_group_names)}.")
                return False
            requested_groups = valid_groups # Use only valid groups

        dbg_info(f"--- Starting Test Execution ---")
        overall_success = True
        total_tests_run = 0
        total_tests_passed = 0
        total_tests_failed = 0
        results_summary = {} # Store results per suite

        try:
            if run_all_tests or "market" in requested_groups:
                dbg_info("\n=== Running Market Test Suite (all) ===")
                market_results = run_market_tests(self.market, ["all"])
                if market_results:
                    results_summary["Market"] = market_results
                    total_tests_run += market_results.get("total", 0)
                    total_tests_passed += market_results.get("passed", 0)
                    total_tests_failed += market_results.get("failed", 0)
                    if market_results.get("failed", 0) > 0:
                        overall_success = False # Mark overall as failed if any suite fails
                dbg_info("=== Market Test Suite Complete ===\n")

            if run_all_tests or "trading" in requested_groups:
                dbg_info("\n=== Running Trading Test Suite (all) ===")
                # Ensure evaluate_instance.flag_development is True for these tests
                # self.evaluate_instance.flag_development = True # Set in __init__
                # Pass both instances to run all applicable trading tests
                trading_results = run_trading_tests(["all"])
                if trading_results:
                    results_summary["Trading"] = trading_results
                    total_tests_run += trading_results.get("total", 0)
                    total_tests_passed += trading_results.get("passed", 0)
                    total_tests_failed += trading_results.get("failed", 0)
                    if trading_results.get("failed", 0) > 0:
                        overall_success = False
                dbg_info("=== Trading Test Suite Complete ===\n")

            if run_all_tests or "broker" in requested_groups:
                dbg_info("\n=== Running Broker Test Suite (all) ===")
                broker_results = run_broker_tests(["all"])
                if broker_results:
                    results_summary["Broker"] = broker_results
                    total_tests_run += broker_results.get("total", 0)
                    total_tests_passed += broker_results.get("passed", 0)
                    total_tests_failed += broker_results.get("failed", 0)
                    if broker_results.get("failed", 0) > 0:
                        overall_success = False # Mark overall as failed if any suite fails
                dbg_info("=== Broker Test Suite Complete ===\n")

            if run_all_tests or "backtest" in requested_groups:
                dbg_info("\n=== Running Backtest Test Suite (all) ===")
                backtest_results = run_backtest_tests(["all"])
                if backtest_results:
                    results_summary["Backtest"] = backtest_results
                    total_tests_run += backtest_results.get("total", 0)
                    total_tests_passed += backtest_results.get("passed", 0)
                    total_tests_failed += backtest_results.get("failed", 0)
                    if backtest_results.get("failed", 0) > 0:
                        overall_success = False # Mark overall as failed if any suite fails
                dbg_info("=== Backtest Test Suite Complete ===\n")

            if run_all_tests or "core" in requested_groups:
                dbg_info("\n=== Running Core Test Suite (all) ===")
                core_results = run_core_tests(["all"])
                if core_results:
                    results_summary["Core"] = core_results
                    total_tests_run += core_results.get("total", 0)
                    total_tests_passed += core_results.get("passed", 0)
                    total_tests_failed += core_results.get("failed", 0)
                    if core_results.get("failed", 0) > 0:
                        overall_success = False
                dbg_info("=== Core Test Suite Complete ===\n")

            if run_all_tests or "integration" in requested_groups:
                dbg_info("\n=== Running Integration Test Suite (all) ===")
                integration_results = run_integration_tests(["all"])
                if integration_results:
                    results_summary["Integration"] = integration_results
                    total_tests_run += integration_results.get("total", 0)
                    total_tests_passed += integration_results.get("passed", 0)
                    total_tests_failed += integration_results.get("failed", 0)
                    if integration_results.get("failed", 0) > 0:
                        overall_success = False
                dbg_info("=== Integration Test Suite Complete ===\n")

            # Add calls to other test group runners here if created later
            # Example:
            # if run_all_tests or "strategy" in requested_groups:
            #     dbg_info("\n=== Running Strategy Test Suite (all) ===")
            #     strategy_results = run_strategy_tests(["all"]) # Assuming this exists
            #     if strategy_results:
            #         results_summary["Strategy"] = strategy_results
            #         total_tests_run += strategy_results.get("total", 0)
            #         total_tests_passed += strategy_results.get("passed", 0)
            #         total_tests_failed += strategy_results.get("failed", 0)
            #         if strategy_results.get("failed", 0) > 0:
            #             overall_success = False
            #     dbg_info("=== Strategy Test Suite Complete ===\n")

        except Exception as e:
            dbg_error(f"An unexpected error occurred during 'test' command execution: {e}")
            dbg_error(traceback.format_exc())
            overall_success = False # Command execution failed

        self.print(f"--- Overall Test Execution Finished ---")
        self.print("=" * 40)

        # Print failed test case titles if any
        failed_suites = [suite for suite, results in results_summary.items() if results.get('failed', 0) > 0]
        if failed_suites:
            self.print(f"{RED}Failed Test Suites:{RESET}")
            for suite_name in failed_suites:
                self.print(f"  - {suite_name}")
            self.print("-" * 40) # Separator for clarity

        self.print("Overall Test Summary:")

        table_data = []
        for suite, results in results_summary.items():
            passed_count = results.get('passed', 0)
            failed_count = results.get('failed', 0)
            # tabulate handles alignment, so we just need the raw numbers or colored strings
            passed_display = f"{GREEN}{passed_count}{RESET}"
            failed_display = f"{RED}{failed_count}{RESET}" if failed_count > 0 else f"{failed_count}"
            table_data.append([suite, results.get('total', 0), passed_display, failed_display])

        # Add total row
        total_passed_display = f"{GREEN}{total_tests_passed}{RESET}"
        total_failed_display = f"{RED}{total_tests_failed}{RESET}" if total_tests_failed > 0 else f"{total_tests_failed}"
        table_data.append(['Total', total_tests_run, total_passed_display, total_failed_display])

        headers = ["Suite", "Ran", "Passed", "Failed"]

        # Generate the table string using tabulate
        table_string = tabulate(table_data, headers=headers, tablefmt="grid")
        self.print(table_string) # Print the generated table
        self.print("=" * 40)

        # Return True if the command ran without crashing AND all tests passed, False otherwise.
        return overall_success and total_tests_failed == 0
