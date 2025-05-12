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
import traceback # For detailed error logging in cmd_market

class TestCLI(CommandLineInterface):
    def __init__(self):
        super().__init__(promote='test') # Initialize parent CLI
        self.market = Market() # Instantiate Market for testing
        self._register_test_commands()

    def _register_test_commands(self):
        """Registers all test commands."""
        # Define available market sub-tests
        self.market_sub_tests = [
            "list_providers",
            "switch_market",
            "get_data_list",
            "get_data",
            "get_info",
            "all" # Special command to run all tests
        ]
        self.regist_cmd(
            "market",
            self.cmd_market,
            description=f"Run tests for market.py. Sub-tests: {', '.join(self.market_sub_tests)}",
            arg_list=self.market_sub_tests,
            group='testing'
        )

        # Define available broker sub-tests (match keys in run_broker_tests)
        self.broker_sub_tests = [
            "initial_state",
            "buy_sufficient_cash",
            "get_position_after_buy",
            "sell_sufficient_position",
            "get_position_after_sell",
            "portfolio_value",
            "buy_insufficient_cash",
            "sell_insufficient_position",
            "summarize_positions",
            "summarize_transactions",
            "save_load_state",
            "transaction_logging",
            "all" # Special command
        ]
        self.regist_cmd(
            "broker",
            self.cmd_broker,
            description=f"Run tests for BrokerManager/BaseBroker. Sub-tests: {', '.join(self.broker_sub_tests)}",
            arg_list=self.broker_sub_tests,
            group='testing'
        )

        # Define top-level test groups
        self.test_groups = ["market", "broker", "all"]
        self.regist_cmd(
            "test",
            self.cmd_test,
            description=f"Run specified test groups or all tests (default). Groups: {', '.join(g for g in self.test_groups if g != 'all')}",
            arg_list=self.test_groups,
            group='testing' # Group for the master test command
        )
        # Add other command registrations if needed

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
                dbg_error(f"No valid test groups specified in: {requested_groups}. Available: market, broker.")
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

        dbg_info(f"--- Overall Test Execution Finished ---")
        dbg_info("=" * 40)
        dbg_info("Overall Test Summary:")
        dbg_info("-" * 40)
        for suite, results in results_summary.items():
            dbg_info(f"  {suite:<10}: Ran={results.get('total', 0)}, Passed={results.get('passed', 0)}, Failed={results.get('failed', 0)}")
        dbg_info("-" * 40)
        dbg_info(f"  {'Total':<10}: Ran={total_tests_run}, Passed={total_tests_passed}, Failed={total_tests_failed}")
        dbg_info("=" * 40)

        # Return True if the command ran without crashing AND all tests passed, False otherwise.
        return overall_success and total_tests_failed == 0
