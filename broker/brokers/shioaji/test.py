import traceback
import datetime as dt
from datetime import date, time # Import date for tracking open date
import os
import argparse # Added for command-line argument parsing

from broker.brokers.shioaji.shioajibroker import ShioajiBroker
from broker.order.constant import OrderStatus, OrderAction, OrderPrice

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

def test_get_last_price():
    print("--- Testing ShioajiBroker get_last_price ---")
    broker = None
    try:
        broker = ShioajiBroker(broker_path='test')
        broker.connect()
        # Use a common stock symbol for testing, e.g., TSMC (2330)
        symbol = '2330'
        last_price = broker.get_last_price(symbol, OrderPrice.LAST)
        print(f"Last price for {symbol}: {last_price}")
    except Exception as e:
        print(f"Error during get_last_price test: {e}")
        traceback_output = traceback.format_exc()
        print(traceback_output)
    finally:
        if broker:
            try:
                broker.disconnect()
                print("ShioajiBroker get_last_price test completed.")
            except NotImplementedError:
                print("ShioajiBroker.disconnect() is not yet implemented.")
            except Exception as e:
                print(f"Error during disconnection: {e}")
    print("--- Test finished ---")

def test_place_buy_order():
    print("--- Testing ShioajiBroker place_buy_order ---")
    broker = None
    try:
        broker = ShioajiBroker(broker_path='test')
        broker.connect()

        symbol = '2330'
        buy_size = 1 # Odd lot
        # Use realistic but fixed prices for testing in simulation
        current_price = broker.get_last_price(symbol, OrderPrice.LAST)
        if current_price == 0:
            # since it's just a test for place order, we ignore get price fail.
            print(f'{symbol} get price fail. Using default price 1000.')
            current_price = 1000
        test_price_buy = current_price + 10

        initial_cash = broker.get_balance()
        print(f"Initial cash: {initial_cash}")
        initial_positions = broker.get_all_positions()
        print(f"Initial positions: {initial_positions}")

        print(f"\n--- Attempting to place a BUY odd lot order for {symbol}@{test_price_buy} ---")
        buy_order_result = broker.place_order(symbol, OrderAction.BUY, buy_size, test_price_buy)

        if buy_order_result:
            print(f"Buy order successful: {buy_order_result}")
        else:
            print("Buy order failed or not filled.")

        # Re-check cash and positions after buy order
        cash_after_buy = broker.get_balance()
        positions_after_buy = broker.get_all_positions()
        print(f"Cash after buy: {cash_after_buy}")
        print(f"Positions after buy: {positions_after_buy}")

    except Exception as e:
        print(f"Error during place_buy_order test: {e}")
        traceback_output = traceback.format_exc()
        print(traceback_output)
    finally:
        if broker:
            try:
                broker.disconnect()
                print("ShioajiBroker place_buy_order test completed.")
            except NotImplementedError:
                print("ShioajiBroker.disconnect() is not yet implemented.")
            except Exception as e:
                print(f"Error during disconnection: {e}")
    print("--- Test finished ---")

def test_place_sell_order():
    print("--- Testing ShioajiBroker place_sell_order ---")
    broker = None
    try:
        broker = ShioajiBroker(broker_path='test')
        broker.connect()

        symbol = '2330'
        sell_size = 1 # Odd lot
        # Use realistic but fixed prices for testing in simulation
        current_price = broker.get_last_price(symbol, OrderPrice.LAST)
        if current_price == 0:
            # since it's just a test for place order, we ignore get price fail.
            print(f'{symbol} get price fail. Using default price 1000.')
            current_price = 1000
        test_price_sell = current_price - 10

        initial_cash = broker.get_balance()
        print(f"Initial cash: {initial_cash}")
        initial_positions = broker.get_all_positions()
        print(f"Initial positions: {initial_positions}")

        print(f"\n--- Attempting to place a SELL odd lot order for {symbol}@{test_price_sell} ---")
        # For sell, we need to ensure we have a position.
        # In a real test, you might place a buy order first, then sell.
        # For this test, we'll just try to sell, acknowledging it might fail if no position.
        sell_order_result = broker.place_order(symbol, OrderAction.SELL, sell_size, test_price_sell)

        if sell_order_result:
            print(f"Sell order successful: {sell_order_result}")
        else:
            print("Sell order failed or not filled (might not have position).")

        # Re-check cash and positions after sell order
        final_cash = broker.get_balance()
        final_positions = broker.get_all_positions()
        print(f"Final cash: {final_cash}")
        print(f"Final positions: {final_positions}")

    except Exception as e:
        print(f"Error during place_sell_order test: {e}")
        traceback_output = traceback.format_exc()
        print(traceback_output)
    finally:
        if broker:
            try:
                broker.disconnect()
                print("ShioajiBroker place_sell_order test completed.")
            except NotImplementedError:
                print("ShioajiBroker.disconnect() is not yet implemented.")
            except Exception as e:
                print(f"Error during disconnection: {e}")
    print("--- Test finished ---")

def test_get_balance():
    # test for get_balance
    print("--- Testing ShioajiBroker get_balance ---")
    broker = None
    try:
        broker = ShioajiBroker(broker_path='test')
        broker.connect()
        cash = broker.get_balance()
        print(f"Current cash balance: {cash}")
    except Exception as e:
        print(f"Error during get_balance test: {e}")
        traceback_output = traceback.format_exc()
        print(traceback_output)
    finally:
        if broker:
            try:
                broker.disconnect()
                print("ShioajiBroker get_balance test completed.")
            except NotImplementedError:
                print("ShioajiBroker.disconnect() is not yet implemented.")
            except Exception as e:
                print(f"Error during disconnection: {e}")
    print("--- Test finished ---")

def test_get_portfolio_value():
    print("--- Testing ShioajiBroker get_portfolio_value ---")
    broker = None
    try:
        broker = ShioajiBroker(broker_path='test')
        broker.connect()
        portfolio_value = broker.get_portfolio_value()
        print(f"Current portfolio value: {portfolio_value}")
    except Exception as e:
        print(f"Error during get_portfolio_value test: {e}")
        traceback_output = traceback.format_exc()
        print(traceback_output)
    finally:
        if broker:
            try:
                broker.disconnect()
                print("ShioajiBroker get_portfolio_value test completed.")
            except NotImplementedError:
                print("ShioajiBroker.disconnect() is not yet implemented.")
            except Exception as e:
                print(f"Error during disconnection: {e}")
    print("--- Test finished ---")

def test_get_positions():
    print("--- Testing ShioajiBroker get_all_positions and get_position_by_symbol ---")
    broker = None
    try:
        broker = ShioajiBroker(broker_path='test')
        broker.connect()
        positions = broker.get_all_positions()

        if positions:
            print("Current positions (from get_all_positions):")
            for symbol, position in positions.items():
                print(f"  {symbol}: {position}")

            print("\n--- Testing get_position_by_symbol for existing positions ---")
            for symbol, _ in positions.items():
                pos_by_sym = broker.get_position_by_symbol(symbol)
                print(f"  get_position_by_symbol for '{symbol}': {pos_by_sym}")
        else:
            print("No positions found via get_all_positions. Skipping tests for existing symbols.")

        print("\n--- Testing get_position_by_symbol for a non-existent symbol ---")
        symbol_not_held = 'NONEXISTENT_SYMBOL_XYZ' # Use a very unlikely symbol
        position_not_held = broker.get_position_by_symbol(symbol_not_held)
        print(f"  get_position_by_symbol for '{symbol_not_held}': {position_not_held}")

    except Exception as e:
        print(f"Error during position tests: {e}")
        traceback_output = traceback.format_exc()
        print(traceback_output)
    finally:
        if broker:
            try:
                broker.disconnect()
                print("ShioajiBroker position tests completed.")
            except NotImplementedError:
                print("ShioajiBroker.disconnect() is not yet implemented.")
            except Exception as e:
                print(f"Error during disconnection: {e}")
    print("--- Test finished ---")


def main():
    # Map test names to functions
    test_functions = {
        "connection": test_connection,
        "get_balance": test_get_balance,
        "get_positions": test_get_positions,
        "get_portfolio_value": test_get_portfolio_value,
        "get_last_price": test_get_last_price,
        "place_buy_order": test_place_buy_order,
        "place_sell_order": test_place_sell_order,
        # Add other test functions here as they are created
    }

    parser = argparse.ArgumentParser(description="Run ShioajiBroker tests.")
    parser.add_argument(
        "-t", "--test-name",
        type=str,
        help=f"Specify a single test function to run (e.g., 'connection'). Available tests: {', '.join(test_functions.keys())}."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all available test functions."
    )

    args = parser.parse_args()

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

