
from typing import Type, Dict, Any, Optional
import os
from tabulate import tabulate # Import tabulate for creating tables

# Local file
from utility.debug import * # Replace standard logging with custom debug system

# Assuming BaseBroker is the primary implementation for now
from broker.base.basebroker import BaseBroker, Position
from core.config import *



class BrokerManager:
    """
    Manages different broker implementations, providing a unified interface.
    Acts as a wrapper around a specific broker instance.
    """
    def __init__(self, broker_type: str = 'base', **kwargs: Any):
        """
        Initializes the BrokerManager with a specific broker type.

        Args:
            broker_type (str): The type of broker to instantiate ('base', etc.). Defaults to 'base'.
            **kwargs: Arguments to pass to the underlying broker's constructor
                      (e.g., initial_cash, commission_per_trade, state_filepath).
        """
        self.cm = AppConfigManager()
        self.broker: BaseBroker # Type hint for the wrapped broker instance
        self.broker_type = broker_type

        if broker_type == 'base':
            # Extract relevant kwargs for BaseBroker, providing defaults if not present
            initial_cash = kwargs.get('initial_cash', 1000000.0)
            commission_per_trade = kwargs.get('commission_per_trade', 5.0)
            # Use os.path.join for correct path construction
            state_filepath = kwargs.get('state_filepath', os.path.join(self.cm.get_path('broker'), f'{broker_type}_state')) # Default path

            self.broker = BaseBroker(
                initial_cash=initial_cash,
                commission_per_trade=commission_per_trade
            )
            # Set the state file path after initialization
            self.broker.set_state_filepath(state_filepath)
            dbg_info(f"Initialized BaseBroker via BrokerManager. Cash: ${initial_cash:,.2f}, Commission: ${commission_per_trade:.2f}, State File: {state_filepath}")
        # Add elif blocks here for other broker types in the future
        # elif broker_type == 'interactive_brokers':
        #     self.broker = InteractiveBrokersBroker(**kwargs)
        else:
            dbg_error(f"Unsupported broker type: {broker_type}")
            raise ValueError(f"Unsupported broker type: {broker_type}")

    def place_order(self, symbol: str, action: str, size: int, price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Places an order through the managed broker.

        Args:
            symbol (str): The stock symbol.
            action (str): 'buy' or 'sell'.
            size (int): The order quantity (must be positive).
            price (Optional[float]): The limit price. If None, treat as market order. Defaults to None.

        Returns:
            Optional[Dict[str, Any]]: Details of the execution, or None if rejected/failed.
        """
        return self.broker.place_order(symbol, action, size, price)

    def get_cash(self) -> float:
        """Returns the current available cash balance from the managed broker."""
        return self.broker.get_cash()

    def get_position_by_symbol(self, symbol: str) -> Position:
        """
        Returns the Position object for a given symbol from the managed broker.
        If the symbol is not held, returns a Position object with size 0.
        """
        return self.broker.get_position_by_symbol(symbol)

    def get_all_positions(self) -> Dict[str, Position]:
        """Returns a dictionary of all current positions from the managed broker."""
        return self.broker.get_all_positions()

    def get_last_price(self, symbol: str) -> float:
        """
        Returns the last known market price for a symbol from the managed broker.
        """
        # Note: This might need adjustment if different brokers handle price fetching differently.
        return self.broker.get_last_price(symbol)

    def get_portfolio_value(self) -> float:
        """
        Calculates the total value of the portfolio using the managed broker.
        """
        return self.broker.get_portfolio_value()

    def set_state_filepath(self, filepath: str):
        """
        Sets the default file path for saving/loading state in the managed broker.

        Args:
            filepath (str): The new default path for the state file.
        """
        self.broker.set_state_filepath(filepath)

    def summarize_positions(self):
        """
        Prints a summary table of all current positions held by the managed broker,
        including market value and unrealized profit/loss.
        """
        positions = self.broker.get_all_positions()
        if not positions:
            print("No positions currently held.")
            return

        headers = [
            "Symbol", "Size", "Avg Entry", "Initial Entry", "Open Date",
            "Market Price", "Market Value", "Cost Basis", "Unrealized P/L"
        ]
        table_data = []
        total_market_value = 0.0
        total_cost_basis = 0.0
        total_unrealized_pl = 0.0

        dbg_info("Summarizing positions...")
        for symbol, pos in positions.items():
            try:
                current_price = self.broker.get_last_price(symbol)
                if current_price <= 0:
                    dbg_warning(f"Could not get valid market price for {symbol}, using 0.0 for calculations.")
                    current_price = 0.0 # Handle case where price might be invalid

                market_value = pos.size * current_price
                cost_basis = pos.size * pos.average_entry_price
                unrealized_pl = market_value - cost_basis

                # Add to totals
                total_market_value += market_value
                total_cost_basis += cost_basis
                total_unrealized_pl += unrealized_pl

                # Format data for the table row
                row = [
                    pos.symbol,
                    pos.size,
                    f"{pos.average_entry_price:,.2f}",
                    f"{pos.initial_entry_price:,.2f}",
                    pos.open_date.isoformat() if pos.open_date else 'N/A',
                    f"{current_price:,.2f}",
                    f"{market_value:,.2f}",
                    f"{cost_basis:,.2f}",
                    f"{unrealized_pl:,.2f}"
                ]
                table_data.append(row)
                dbg_debug(f"Position Row Data for {symbol}: {row}")

            except Exception as e:
                dbg_error(f"Error processing position for {symbol}: {e}")
                # Optionally add a row indicating an error for this symbol
                table_data.append([symbol, pos.size, 'Error', 'Error', 'Error', 'Error', 'Error', 'Error', 'Error'])


        # Use tabulate to create the table string
        # Using 'grid' format for clear borders, 'floatfmt' for default float formatting (though we pre-format above)
        try:
            table_str = tabulate(table_data, headers=headers, tablefmt="grid", stralign="right")
            print("\n--- Current Positions Summary ---")
            print(table_str)

            # Print Totals
            print("\n--- Portfolio Totals ---")
            print(f"Total Market Value: ${total_market_value:,.2f}")
            print(f"Total Cost Basis:   ${total_cost_basis:,.2f}")
            print(f"Total Unrealized P/L: ${total_unrealized_pl:,.2f}")
            print("-" * 26) # Separator

        except Exception as e:
            dbg_error(f"Error generating position summary table with tabulate: {e}")
            print("\nError: Could not generate position summary table.")


    def connect(self):
        """
        Connects the underlying managed broker.
        For BaseBroker, this loads the state. For live brokers, this would establish a connection.
        """
        # dbg_info(f"BrokerManager: Initiating connection for {self.broker_type} broker...")
        try:
            self.broker.connect()
            dbg_trace(f"BrokerManager: Connection process completed for {self.broker_type} broker.")
        except Exception as e:
            dbg_error(f"BrokerManager: Error during connection for {self.broker_type} broker: {e}")
            # Optionally re-raise or handle specific connection errors
            raise

    def disconnect(self):
        """
        Disconnects the underlying managed broker.
        For BaseBroker, this saves the state. For live brokers, this would close the connection.
        """
        # dbg_info(f"BrokerManager: Initiating disconnection for {self.broker_type} broker...")
        try:
            self.broker.disconnect()
            dbg_trace(f"BrokerManager: Disconnection process completed for {self.broker_type} broker.")
        except Exception as e:
            dbg_error(f"BrokerManager: Error during disconnection for {self.broker_type} broker: {e}")
            # Optionally re-raise or handle specific disconnection errors
            raise

    # You might add other broker-specific methods here as needed,
    # potentially checking self.broker_type if they aren't universal.

if __name__ == "__main__":
    # Example usage relies on utility.debug now
    print("--- Starting BrokerManager Example ---")

    # Define a state file path for this example
    example_state_file = "data/broker_manager_example_state.json"
    import os
    # Ensure the data directory exists
    os.makedirs(os.path.dirname(example_state_file), exist_ok=True)

    # --- Initialize BrokerManager with BaseBroker ---
    print("\n--- Initializing BrokerManager ---")
    try:
        # Use specific parameters for the example
        manager = BrokerManager(
            broker_type='base',
            initial_cash=100000.0,
            commission_per_trade=7.0,
            state_filepath=example_state_file
        )
        print(f"BrokerManager initialized with {manager.broker_type} broker.")
        print(f"Initial Cash: ${manager.get_cash():,.2f}")
        print(f"State file path: {manager.broker.state_filepath}") # Access underlying broker's path for confirmation

    except ValueError as e:
        print(f"Error initializing BrokerManager: {e}")
        exit() # Exit if initialization fails

    # --- Place Orders via Manager ---
    print("\n--- Placing Orders ---")
    # Assuming BaseBroker's get_last_price works or is mocked appropriately for a real scenario
    # For this example, BaseBroker might use its default fake price or market data if available
    # Let's assume '2330' price is around 150 for illustration
    product_price = manager.get_last_price("2330")
    exec_result1 = manager.place_order(symbol="2330", action="buy", size=50, price=product_price + 10) # Limit buy (should fill if market <= 160)
    print(f"Place Buy Order 2330 (Limit 160): {exec_result1}")
    exec_result2 = manager.place_order(symbol="2330", action="buy", size=20, price=None) # Market buy
    print(f"Place Buy Order 2330 (Market): {exec_result2}")
    exec_result3 = manager.place_order(symbol="MSFT", action="buy", size=30) # Market buy (implicit None price)
    print(f"Place Buy Order MSFT (Market): {exec_result3}")
    exec_result4 = manager.place_order(symbol="2330", action="sell", size=10, price=product_price - 10) # Limit sell (should fill if market >= 140)
    print(f"Place Sell Order 2330 (Limit 140): {exec_result4}")
    exec_result_fail = manager.place_order(symbol="2330", action="sell", size=1000) # Try to sell more than owned
    print(f"Place Sell Order 2330 (Fail - Insufficient): {exec_result_fail}")


    # --- Check State via Manager ---
    print("\n--- Checking State ---")
    print(f"Current Cash: ${manager.get_cash():,.2f}")
    print("Current Positions:")
    positions = manager.get_all_positions()
    if not positions:
        print("  No positions held.")
    for symbol, pos in positions.items():
        print(f"  {pos}")
    # Note: Portfolio value depends on the underlying broker's get_last_price implementation
    print(f"Estimated Portfolio Value: ${manager.get_portfolio_value():,.2f}")

    # --- Summarize Positions ---
    manager.summarize_positions()

    # --- Disconnect Manager (Saves State) ---
    print("\n--- Disconnecting Manager (saves state) ---")
    manager.disconnect() # Disconnects and saves state to the default path (example_state_file)
    print(f"State saved implicitly via disconnect to {manager.broker.state_filepath}")

    # --- Create New Manager and Connect (Loads State) ---
    print("\n--- Creating New Manager and Connecting (loads state) ---")
    manager2 = BrokerManager(
        broker_type='base',
        initial_cash=5000.0, # Different initial cash, will be overwritten by loaded state
        commission_per_trade=1.0, # Different commission, will be overwritten by loaded state
        state_filepath=example_state_file # Must point to the same file to load
    )
    print(f"Manager 2 Initial Cash (before connect): ${manager2.get_cash():,.2f}")
    manager2.connect() # Connects and loads state from the file
    print("State loaded implicitly via connect.")

    # --- Verify Loaded State in New Manager ---
    print("\n--- Verifying Loaded State (Manager 2) ---")
    print(f"Manager 2 Loaded Cash: ${manager2.get_cash():,.2f}")
    print("Manager 2 Loaded Positions:")
    loaded_positions = manager2.get_all_positions()
    if not loaded_positions:
        print("  No positions loaded.")
    for symbol, pos in loaded_positions.items():
        print(f"  {pos}") # Keep simple print for basic verification

    # --- Summarize Positions for Manager 2 ---
    manager2.summarize_positions()

    # Disconnect manager2 (optional, saves state again)
    print("\n--- Disconnecting Manager 2 ---")
    manager2.disconnect()

    # --- Clean up the example state file ---
    try:
        if os.path.exists(example_state_file):
            os.remove(example_state_file)
            print(f"\nCleaned up example state file: {example_state_file}")
        # Attempt to remove the data directory if it's empty
        if os.path.exists("data") and not os.listdir("data"):
             os.rmdir("data")
             print("Cleaned up empty data directory.")
    except OSError as e:
        print(f"\nError cleaning up: {e}")


    print("--- BrokerManager Example Finished ---")
