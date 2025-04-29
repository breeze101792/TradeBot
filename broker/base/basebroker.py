import json
import os
from datetime import date # Import date for tracking open date
from utility.debug import *

from market.market import *

class Position:
    """Represents a holding in a specific asset."""
    def __init__(self, symbol: str, size: int = 0, average_entry_price: float = 0.0, initial_entry_price: float = 0.0, open_date: date | None = None):
        self.symbol = symbol
        self.size = size
        self.average_entry_price = average_entry_price
        # Store the price of the very first buy transaction for this position instance
        self.initial_entry_price = initial_entry_price
        # Store the date when the position was first opened
        self.open_date = open_date

    def update(self, action: str, size: int, price: float):
        """Updates the position based on a transaction."""
        total_cost_before = self.size * self.average_entry_price
        if action == 'buy':
            # Record the price and date of the first buy
            if self.initial_entry_price == 0.0: # Assuming initial price is 0 only before first buy
                self.initial_entry_price = price
            if self.open_date is None: # Record open date only once
                self.open_date = date.today()

            new_total_cost = total_cost_before + (size * price)
            self.size += size
            if self.size != 0:
                self.average_entry_price = new_total_cost / self.size
            else:
                # Should not happen if buying, but handle defensively
                self.average_entry_price = 0.0
        elif action == 'sell':
            # Average entry price doesn't change on sell, PnL is realized
            self.size -= size
            if self.size < 0:
                dbg_warning(f"Position size for {self.symbol} went negative ({self.size}). Resetting to 0.")
                # This indicates an oversell, handle as per strategy logic (e.g., raise error or cap at 0)
                self.size = 0
            if self.size == 0:
                self.average_entry_price = 0.0 # Reset average price when position is closed
                self.initial_entry_price = 0.0 # Also reset initial entry price when closed
                self.open_date = None # Reset open date when closed

    def get_market_value(self, current_price: float) -> float:
        """Calculates the current market value of the position."""
        return self.size * current_price

    def __repr__(self):
        open_date_str = self.open_date.isoformat() if self.open_date else 'N/A'
        return f"Position(symbol='{self.symbol}', size={self.size}, avg_entry={self.average_entry_price:.2f}, initial_entry={self.initial_entry_price:.2f}, open_date='{open_date_str}')"

    def to_dict(self) -> dict:
        """Converts the Position object to a dictionary."""
        return {
            'symbol': self.symbol,
            'size': self.size,
            'average_entry_price': self.average_entry_price,
            'initial_entry_price': self.initial_entry_price,
            # Convert date to ISO string for JSON compatibility, handle None
            'open_date': self.open_date.isoformat() if self.open_date else None
        }


class BaseBroker:
    """
    A basic simulated broker handling cash, positions, and simple order execution.
    This mimics the interface needed by a backtesting or simple trading system.
    """
    def __init__(self, initial_cash: float = 1000000.0, commission_per_trade: float = 5.0):
        """
        Initializes the broker.

        Args:
            initial_cash (float): Starting cash balance.
            commission_per_trade (float): Fixed commission fee for each trade execution.
        """
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.commission_per_trade = commission_per_trade
        self.state_filepath: str = "./broker_state.json" # Default path for saving/loading state
        # positions stores Position objects, keyed by symbol
        self.positions: dict[str, Position] = {}
        self.market = Market()
        self._state_changed: bool = False # Flag to track if state has changed since last load/save
        # dbg_info(f"Broker initialized with Cash: ${self.cash:,.2f}, Commission: ${self.commission_per_trade:.2f}/trade. State file: {self.state_filepath}")

    def place_order(self, symbol: str, action: str, size: int, price: float | None = None) -> dict | None:
        """
        Simulates placing and immediately filling an order.
        If price is None, it's a market order filled at the current market price.
        If price is specified, it acts as a limit:
          - Buy: Executes only if market_price <= price.
          - Sell: Executes only if market_price >= price.
        Execution always happens at the market_price if conditions are met.
        Updates cash and position based on the execution.

        Args:
            symbol (str): The stock symbol.
            action (str): 'buy' or 'sell'.
            size (int): The order quantity (must be positive).
            price (float | None, optional): The limit price. If None, treat as market order. Defaults to None.

        Returns:
            dict: Details of the simulated execution ('filled' status), or None if order rejected.
        """
        if size <= 0:
            dbg_error(f"Order rejected for {symbol}: Size must be positive, got {size}.")
            return None
        if action not in ['buy', 'sell']:
            dbg_error(f"Order rejected for {symbol}: Invalid action '{action}'. Must be 'buy' or 'sell'.")
            return None

        # Get the current market price for execution comparison and potential fill
        market_price = self.get_last_price(symbol)
        if market_price <= 0.0:
             dbg_error(f"Order rejected for {symbol}: Invalid or zero market price ({market_price:.2f}) obtained.")
             return None # Cannot execute at zero or negative price

        # Check limit price condition if specified
        if price is not None:
            if action == 'buy' and market_price > price:
                dbg_warning(f"Buy order for {symbol} rejected: Market price ({market_price:.2f}) > Limit price ({price:.2f})")
                return None
            elif action == 'sell' and market_price < price:
                dbg_warning(f"Sell order for {symbol} rejected: Market price ({market_price:.2f}) < Limit price ({price:.2f})")
                return None
            dbg_debug(f"Limit price condition met for {action} {symbol}: Market Price {market_price:.2f} vs Limit {price:.2f}")
        else:
            dbg_debug(f"Processing as market order for {action} {symbol} at Market Price {market_price:.2f}")


        # --- Execution Logic (uses market_price for calculations) ---
        cost = market_price * size # Cost/Proceeds based on actual market price
        commission = self.commission_per_trade

        dbg_debug(f"Attempting {action} order: {symbol}, Size: {size}, Execution Price: {market_price:.2f}, Cost/Proceeds: {cost:.2f}, Commission: {commission:.2f}")

        if action == 'buy':
            required_cash = cost + commission
            if self.cash < required_cash:
                dbg_warning(f"Order rejected for {symbol}: Insufficient cash. Required: ${required_cash:.2f}, Available: ${self.cash:.2f}")
                return None # Reject order

            # Update cash
            self.cash -= required_cash
            dbg_debug(f"Cash updated after BUY: ${self.cash:.2f}")

            # Update position
            if symbol not in self.positions:
                self.positions[symbol] = Position(symbol)
            self.positions[symbol].update(action, size, market_price) # Use market_price here
            self._state_changed = True
            dbg_info(f"Executed BUY: {symbol}, Size: {size}, Price: {market_price:.2f}. New Position: {self.positions[symbol]}")

        elif action == 'sell':
            current_position = self.get_position_by_symbol(symbol)
            if current_position.size < size:
                dbg_warning(f"Order rejected for {symbol}: Insufficient position to sell. Required: {size}, Available: {current_position.size}")
                return None # Reject order

            # Update cash
            proceeds = cost
            self.cash += (proceeds - commission)
            dbg_debug(f"Cash updated after SELL: ${self.cash:.2f}")

            # Update position
            self.positions[symbol].update(action, size, market_price) # Use market_price here
            self._state_changed = True
            dbg_info(f"Executed SELL: {symbol}, Size: {size}, Price: {market_price:.2f}. New Position: {self.positions[symbol]}")

            # Clean up position if size becomes zero
            if self.positions[symbol].size == 0:
                dbg_debug(f"Position closed for {symbol}. Removing from holdings.")
                del self.positions[symbol]

        # Return simulated execution details
        return {
            'symbol': symbol,
            'action': action,
            'price': market_price, # Return the actual execution price
            'size': size,
            'commission': commission,
            'status': 'filled' # Simple simulation: always filled immediately
        }

    def get_cash(self) -> float:
        """Returns the current available cash balance."""
        return self.cash

    def get_position_by_symbol(self, symbol: str) -> Position:
        """
        Returns the Position object for a given symbol.
        If the symbol is not held, returns a Position object with size 0.
        """
        return self.positions.get(symbol, Position(symbol, size=0, average_entry_price=0.0))

    def get_all_positions(self) -> dict[str, Position]:
        """Returns a dictionary of all current positions."""
        return self.positions.copy() # Return a copy to prevent external modification

    def get_last_price(self, symbol: str) -> float:
        """
        Returns the last known market price for a symbol.
        In this basic simulation, it returns a fixed fake price.
        A real implementation would fetch this from a market data source.
        """
        try:
            result_df = self.market.get_data(symbol)
            if result_df is not None and not result_df.empty:
                # Assuming the DataFrame is sorted chronologically (latest date last)
                # and has a 'Close' column.
                last_price = result_df['Close'].iloc[-1]
                dbg_debug(f"Retrieved last price for {symbol}: {last_price}")
                return float(last_price) # Ensure it's a float
            else:
                dbg_warning(f"Could not get last price for {symbol}: No data returned or DataFrame is empty.")
                return 0.0 # Return 0.0 if no data is available
        except (KeyError, IndexError, TypeError) as e:
            dbg_error(f"Error retrieving last price for {symbol} from DataFrame: {e}")
            return 0.0 # Return 0.0 on error
        except Exception as e:
            dbg_error(f"An unexpected error occurred in get_last_price for {symbol}: {e}")
            return 0.0 # Return 0.0 on unexpected errors

    def get_portfolio_value(self) -> float:
        """
        Calculates the total value of the portfolio (cash + market value of all positions).
        Requires get_last_price to be implemented realistically for accurate valuation.
        """
        holdings_value = 0.0
        for symbol, position in self.positions.items():
            current_price = self.get_last_price(symbol) # Needs real price data
            holdings_value += position.get_market_value(current_price)

        total_value = self.cash + holdings_value
        dbg_debug(f"Portfolio Value Calculation: Cash ${self.cash:,.2f} + Holdings ${holdings_value:,.2f} = Total ${total_value:,.2f}")
        return total_value

    def set_state_filepath(self, filepath: str):
        """
        Sets the default file path for saving and loading the broker state.

        Args:
            filepath (str): The new default path for the state file.
        """
        # Ensure the directory for the state file exists
        dir_name = os.path.dirname(filepath)
        if dir_name: # Check if directory path is not empty
            try:
                os.makedirs(dir_name, exist_ok=True)
                dbg_debug(f"Ensured directory exists: {dir_name}")
            except OSError as e:
                # Log an error if directory creation fails for unexpected reasons
                dbg_error(f"Could not create directory {dir_name} for state file: {e}")
                # Decide if you want to proceed or raise an error/return here
                # For now, we'll just log and continue setting the path

        self.state_filepath = filepath
        dbg_info(f"Broker state file path set to: {self.state_filepath}")

    def _save_state(self, filepath: str | None = None):
        """
        Saves the current broker state (cash and positions) to a JSON file.

        Args:
            filepath (str | None): The path to save the state file. If None, uses the default path stored in self.state_filepath.
        """
        save_path = filepath if filepath is not None else self.state_filepath
        state = {
            'cash': self.cash,
            'positions': {symbol: pos.to_dict() for symbol, pos in self.positions.items()}
        }
        try:
            # Ensure directory exists if filepath includes directories
            dir_name = os.path.dirname(save_path)
            if dir_name: # Check if directory path is not empty
                os.makedirs(dir_name, exist_ok=True)

            with open(save_path, 'w') as f:
                json.dump(state, f, indent=4)
            dbg_info(f"Broker state saved successfully to {save_path}")
        except IOError as e:
            dbg_error(f"Failed to save broker state to {save_path}: {e}")

    def _load_state(self, filepath: str | None = None):
        """
        Loads the broker state (cash and positions) from a JSON file.

        Args:
            filepath (str | None): The path to load the state file from. If None, uses the default path stored in self.state_filepath.
        """
        load_path = filepath if filepath is not None else self.state_filepath
        if not os.path.exists(load_path):
            dbg_warning(f"State file {load_path} not found. Initializing with default state.")
            # Optionally, you could reset to initial state here or just do nothing
            # self.cash = self.initial_cash
            # self.positions = {}
            return

        try:
            with open(load_path, 'r') as f:
                state = json.load(f)

            self.cash = state.get('cash', self.initial_cash) # Load cash, default to initial if missing
            loaded_positions = state.get('positions', {})
            self.positions = {} # Clear current positions before loading

            for symbol, pos_data in loaded_positions.items():
                # Load open_date string and convert back to date object
                open_date_str = pos_data.get('open_date') # Get string or None
                loaded_open_date = None
                if open_date_str:
                    try:
                        loaded_open_date = date.fromisoformat(open_date_str)
                    except (TypeError, ValueError):
                        dbg_warning(f"Could not parse open_date '{open_date_str}' for symbol {symbol}. Setting to None.")

                # Recreate Position objects from the loaded dictionary data
                self.positions[symbol] = Position(
                    symbol=pos_data['symbol'],
                    size=pos_data['size'],
                    average_entry_price=pos_data['average_entry_price'],
                    # Load initial entry price, default to 0.0 if missing (backward compatibility)
                    initial_entry_price=pos_data.get('initial_entry_price', 0.0),
                    # Assign the loaded (or None) open_date
                    open_date=loaded_open_date
                )
            dbg_info(f"Broker state loaded successfully from {load_path}. Cash: ${self.cash:,.2f}, Positions: {len(self.positions)}")

        except (IOError, json.JSONDecodeError, KeyError, TypeError) as e:
            dbg_error(f"Failed to load or parse broker state from {load_path}: {e}. Using existing/default state.")
            # Decide how to handle errors: keep current state, reset, or raise exception
    def connect(self):
        """
        Connects the simulated broker. For BaseBroker, this means loading the last saved state.
        """
        dbg_info(f"Connecting BaseBroker: Loading state from {self.state_filepath}...")
        self._load_state() # Load state using the configured filepath

    def disconnect(self):
        """
        Disconnects the simulated broker. For BaseBroker, this means saving the current state
        if it has changed since the last load or save.
        """
        if self._state_changed:
            dbg_info(f"Disconnecting BaseBroker: State changed, saving state to {self.state_filepath}...")
            self._save_state() # Save state using the configured filepath
        else:
            dbg_info(f"Disconnecting BaseBroker: State unchanged since last load/save, skipping save to {self.state_filepath}.")


if __name__ == "__main__":
    # --- Example Usage ---
    dbg_info("--- Starting Broker Example ---")

    # 1. Initialize Broker
    broker1 = BaseBroker(initial_cash=50000, commission_per_trade=4.95)
    print(f"Initial Cash: ${broker1.get_cash():,.2f}")

    # 2. Place Orders (Market and Limit Examples)
    print("\n--- Placing Orders ---")
    # Assuming get_last_price("2330") returns ~150 and get_last_price("2454") returns ~2500 for illustration
    # Market Orders (price=None)
    print("--- Market Orders ---")
    exec_buy_market = broker1.place_order(symbol="2330", action="buy", size=10) # Market buy
    print(f"Market Buy 2330 Execution: {exec_buy_market}")
    exec_sell_market = broker1.place_order(symbol="2330", action="sell", size=5) # Market sell
    print(f"Market Sell 2330 Execution: {exec_sell_market}")

    # Limit Orders
    print("\n--- Limit Orders ---")
    # Buy Limit - Should execute if market <= 160 (assuming market is ~150)
    exec_buy_limit_ok = broker1.place_order(symbol="2330", action="buy", size=5, price=160.00)
    print(f"Limit Buy 2330 (Limit=160.00) Execution (expect success): {exec_buy_limit_ok}")
    # Buy Limit - Should fail if market > 140 (assuming market is ~150)
    exec_buy_limit_fail = broker1.place_order(symbol="2330", action="buy", size=5, price=140.00)
    print(f"Limit Buy 2330 (Limit=140.00) Execution (expect fail): {exec_buy_limit_fail}")

    # Sell Limit - Should execute if market >= 145 (assuming market is ~150)
    exec_sell_limit_ok = broker1.place_order(symbol="2330", action="sell", size=2, price=145.00)
    print(f"Limit Sell 2330 (Limit=145.00) Execution (expect success): {exec_sell_limit_ok}")
    # Sell Limit - Should fail if market < 160 (assuming market is ~150)
    exec_sell_limit_fail = broker1.place_order(symbol="2330", action="sell", size=2, price=160.00)
    print(f"Limit Sell 2330 (Limit=160.00) Execution (expect fail): {exec_sell_limit_fail}")

    # Order Failure (Insufficient Funds/Position)
    print("\n--- Order Failures ---")
    exec_buy_fail_cash = broker1.place_order(symbol="2454", action="buy", size=100) # Should fail (insufficient cash)
    print(f"Buy 2454 Execution (expect fail - cash): {exec_buy_fail_cash}")
    # Sell more than owned (check current position size after previous trades)
    current_2330_pos = broker1.get_position_by_symbol("2330").size
    exec_sell_fail_pos = broker1.place_order(symbol="2330", action="sell", size=current_2330_pos + 1) # Try to sell more than held
    print(f"Sell 2330 Execution (expect fail - position): {exec_sell_fail_pos}")


    # 3. Check State
    print("\n--- Current Broker State (broker1) ---")
    print(f"Current Cash: ${broker1.get_cash():,.2f}")
    print("Current Positions:")
    all_positions = broker1.get_all_positions()
    if not all_positions:
        print("  No positions held.")
    for symbol, pos in all_positions.items():
        print(f"  {pos}")
    # Note: Portfolio value uses the latest market price via get_last_price
    print(f"Estimated Portfolio Value: ${broker1.get_portfolio_value():,.2f}")

    # 4. Disconnect broker1 (saves state to default path)
    print("\n--- Disconnecting broker1 (saves state) ---")
    broker1.disconnect()

    # 5. Create broker2 and connect (loads state from default path)
    print("\n--- Creating broker2 and Connecting (loads state) ---")
    # Initialize broker2 with a different initial cash to show loading works
    # It will use the default state_filepath: "./broker_state.json"
    broker2 = BaseBroker(initial_cash=10000, commission_per_trade=4.95)
    print(f"broker2 Initial Cash (before connect): ${broker2.get_cash():,.2f}")
    broker2.connect() # Connects and loads state from "./broker_state.json"

    # 6. Verify Loaded State in broker2
    print("\n--- Verifying Loaded State (broker2) ---")
    print(f"broker2 Loaded Cash: ${broker2.get_cash():,.2f}")
    print("broker2 Loaded Positions:")
    loaded_positions_b2 = broker2.get_all_positions()
    if not loaded_positions_b2:
        print("  No positions loaded.")
    for symbol, pos in loaded_positions_b2.items():
        print(f"  {pos}")
    broker2.disconnect() # Disconnect broker2 (saves state again, optional here)

    # 7. Demonstrate Custom Filepath with connect/disconnect
    print("\n--- Demonstrating Custom Filepath with connect/disconnect ---")
    custom_path = "data/custom_broker_state.json"
    # Initialize broker_custom with the custom path
    broker_custom = BaseBroker(initial_cash=75000, commission_per_trade=1.00, state_filepath=custom_path)
    print(f"\nCreated broker_custom. Initial Cash: ${broker_custom.get_cash():,.2f}, State File: {broker_custom.state_filepath}")
    # Perform some actions
    broker_custom.place_order(symbol="AAPL", action="buy", size=50)
    print("broker_custom Positions after buy:")
    for symbol, pos in broker_custom.get_all_positions().items(): print(f"  {pos}")
    # Disconnect broker_custom (saves state to custom_path)
    print("Disconnecting broker_custom (saves state)...")
    broker_custom.disconnect()

    # Create broker3, using the custom path, and connect
    print("\nCreating broker3 with custom path and Connecting...")
    broker3 = BaseBroker(initial_cash=1000, commission_per_trade=1.00, state_filepath=custom_path)
    print(f"broker3 Initial Cash (before connect): ${broker3.get_cash():,.2f}")
    broker3.connect() # Connects and loads state from custom_path

    # Verify loaded state in broker3
    print(f"broker3 Loaded Cash from {custom_path}: ${broker3.get_cash():,.2f}")
    print("broker3 Loaded Positions:")
    loaded_positions_b3 = broker3.get_all_positions()
    if not loaded_positions_b3:
        print("  No positions loaded.")
    for symbol, pos in loaded_positions_b3.items():
        print(f"  {pos}")
    broker3.disconnect() # Disconnect broker3

    # Clean up the created state files if desired
    default_state_file = "./broker_state.json"
    try:
        if os.path.exists(default_state_file):
            os.remove(default_state_file)
            print(f"\nCleaned up default state file: {default_state_file}")
        if os.path.exists(custom_path):
            os.remove(custom_path)
            print(f"Cleaned up custom state file: {custom_path}")
        custom_dir = os.path.dirname(custom_path)
        if custom_dir and os.path.exists(custom_dir) and not os.listdir(custom_dir): # Check if dir exists and is empty
             os.rmdir(custom_dir)
             print(f"Cleaned up directory: {custom_dir}")
    except OSError as e:
        print(f"\nError cleaning up state files/directory: {e}")

    dbg_info("--- Broker Example Finished ---")

