import traceback
import datetime as dt
from datetime import date, time # Import date for tracking open date
import os
import argparse # Added for command-line argument parsing

from broker.shioaji.shioajibroker import ShioajiBroker

def test_connection():
    # test for account connect/disconnect
    print("--- Testing ShioajiBroker connect/disconnect ---")
    broker = None
    try:
        broker = ShioajiBroker(broker_path = 'test')
        api = broker.connect()
        print("ShioajiBroker connected successfully.")
        # In a real scenario, you might perform some operations here
        # For this test, we just connect and then disconnect
    except Exception as e:
        print(f"Error during connection: {e}")
    
        traceback_output = traceback.format_exc()
        print(traceback_output)
    finally:
        if broker:
            try:
                # Disconnect is an abstract method, so it will raise NotImplementedError
                # if not implemented in ShioajiBroker.
                # For this test, we'll just print a message indicating it should be implemented.
                broker.disconnect() # Uncomment this line once disconnect is implemented
                print("ShioajiBroker disconnect test completed.")
            except NotImplementedError:
                print("ShioajiBroker.disconnect() is not yet implemented.")
            except Exception as e:
                print(f"Error during disconnection: {e}")
    print("--- Test finished ---")

def test_get_info():
    # test for get_cash
    print("--- Testing ShioajiBroker get_cash ---")
    broker = None
    try:
        broker = ShioajiBroker(broker_path='test')
        broker.connect()
        cash = broker.get_cash()
        print(f"Current cash balance: {cash}")
    except Exception as e:
        print(f"Error during get_cash test: {e}")
        traceback_output = traceback.format_exc()
        print(traceback_output)
    finally:
        if broker:
            try:
                broker.disconnect()
                print("ShioajiBroker get_cash test completed.")
            except NotImplementedError:
                print("ShioajiBroker.disconnect() is not yet implemented.")
            except Exception as e:
                print(f"Error during disconnection: {e}")
    print("--- Test finished ---")


def main():
    parser = argparse.ArgumentParser(description="Run ShioajiBroker tests.")
    parser.add_argument(
        "--test-name",
        type=str,
        help="Specify a single test function to run (e.g., 'connection')."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all available test functions."
    )

    args = parser.parse_args()

    # Map test names to functions
    test_functions = {
        "connection": test_connection,
        "get_info": test_get_info, # Added test_get_info
        # Add other test functions here as they are created
    }

    if args.all:
        print("Running all tests...")
        for test_name, func in test_functions.items():
            print(f"\n--- Running test: {test_name} ---")
            func()
            print(f"--- Finished test: {test_name} ---")
    elif args.test_name:
        test_to_run = args.test_name.lower()
        if test_to_run in test_functions:
            print(f"Running specified test: {test_to_run}")
            test_functions[test_to_run]()
        else:
            print(f"Error: Test function '{args.test_name}' not found.")
            print(f"Available tests: {', '.join(test_functions.keys())}")
    else:
        # Default behavior if no arguments are provided, or provide help
        parser.print_help()
        print("\nNo test specified. Use --test-name or --all.")

if __name__ == "__main__":
    main()

