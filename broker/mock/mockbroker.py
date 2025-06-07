import json
import os
import datetime as dt
from datetime import date, time, datetime # Import date and datetime for tracking open date and order events
from enum import Enum # Import Enum
from dataclasses import dataclass, field # Import field
from typing import Any, Optional, Dict # Import Any, Optional, Dict

from utility.debug import *

from market.market import *
from market.provider.twse import *
from broker.mock.mockorder import MockOrder
from broker.base.position import Position
from broker.base.basebroker import BaseBroker
from broker.ordertracker import OrderTracker
from broker.event import Event

class MockBroker(BaseBroker):
    """
    A basic simulated broker handling cash, positions, and simple order execution.
    This mimics the interface needed by a backtesting or simple trading system.
    """
    def __init__(self, initial_cash: float = 1000000.0, commission_rate: float = 0.003, simulation = True, **kargs):
        """
        Initializes the broker.

        Args:
            initial_cash (float): Starting cash balance.
            commission_rate (float): Fixed commission fee for each trade execution.
        """
        super().__init__(**kargs)

        self.simulation=simulation
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.commission_rate = commission_rate

        self.state_filepath: str = os.path.join(self.broker_path, "broker_state.json") # Default path for saving/loading state
        # positions stores Position objects, keyed by symbol
        self.positions: dict[str, Position] = {}
        self.market = Market()
        self.data_provider = TWSE()
        # self._state_changed: bool = False # Flag to track if state has changed since last load/save
        # dbg_info(f"Broker initialized with Cash: ${self.cash:,.2f}, Commission: ${self.commission_rate:.2f}/trade. State file: {self.state_filepath}")

    def is_market_open(self) -> bool:
        """
        Checks if the market is currently open.
        TWSE market hours: Monday to Friday, 9:00 AM to 1:25 PM.
        """
        if self.simulation is True:
            return True
        now = datetime.now()
        current_time = now.time()
        current_weekday = now.weekday()  # Monday is 0 and Sunday is 6

        # Market is open on weekdays (Monday to Friday)
        if current_weekday >= 5: # Saturday or Sunday
            dbg_trace("Market is closed: It's a weekend.")
            return False

        # Define market open and close times
        market_open_time = dt.time(9, 0, 0)
        market_close_time = dt.time(13, 25, 0) # Market closes at 13:25 for matching

        if market_open_time <= current_time <= market_close_time:
            dbg_trace("Market is open.")
            return True
        else:
            dbg_trace(f"Market is closed: Current time {current_time.strftime('%H:%M:%S')} is outside trading hours ({market_open_time.strftime('%H:%M:%S')} - {market_close_time.strftime('%H:%M:%S')}).")
            return False

    def _create_order_tracker(self, order: MockOrder) -> OrderTracker:
        """
        Creates an OrderTracker instance from a MockOrder object.
        """
        tracker = OrderTracker(
            timestamp=order.timestamp,
            symbol=order.symbol,
            action=order.action,
            size=order.size,
            price=order.price,
            commission=order.commission,
            status=order.status,
            reason=order.reason
        )
        tracker.order_instance = order # Link the original order instance
        return tracker

    def update_order_status(self, order_tracker: OrderTracker):
        """
        Updates the OrderTracker with the latest information from its internal order instance.
        In a real broker, this would involve querying the broker's API for order status updates.
        For MockBroker, the order_tracker is already created with the final status,
        so this function primarily serves as a placeholder and ensures consistency.
        """
        # In a mock, the order_tracker's order_instance already holds the final state.
        # We explicitly copy the fields to the tracker itself to fulfill the "update" concept.
        if order_tracker.order_instance:
            order_tracker.timestamp = order_tracker.order_instance.timestamp
            order_tracker.symbol = order_tracker.order_instance.symbol
            order_tracker.action = order_tracker.order_instance.action
            order_tracker.size = order_tracker.order_instance.size
            order_tracker.price = order_tracker.order_instance.price
            order_tracker.commission = order_tracker.order_instance.commission
            order_tracker.status = order_tracker.order_instance.status
            order_tracker.reason = order_tracker.order_instance.reason
            dbg_debug(f"OrderTracker updated for {order_tracker.symbol} to status: {order_tracker.status}")
        else:
            dbg_warning("Cannot update OrderTracker: order_instance is missing.")

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
        # For the mock function, we return with callback. it help us to test return different kind of event.
        # but in real broker, this event only been sent wtih API response.
        # if the issue is on our own, we could just fix it or return false/raise a exception.
        if not self.is_market_open():
            reason = "Market is closed."
            dbg_warning(f"Order rejected for {symbol}: {reason}")
            return None

        if size <= 0:
            reason = f"Size must be positive, got {size}."
            dbg_error(f"Order rejected for {symbol}: {reason}")
            return None

        if action not in ['buy', 'sell']:
            reason = f"Invalid action '{action}'. Must be 'buy' or 'sell'."
            dbg_error(f"Order rejected for {symbol}: {reason}")
            return None

        # Get the current market price for execution comparison and potential fill
        market_price = self.get_last_price(symbol)
        if market_price <= 0.0:
             reason = f"Invalid or zero market price ({market_price:.2f}) obtained."
             dbg_error(f"Order rejected for {symbol}: {reason}")
             return None # Cannot execute at zero or negative price

        # Check limit price condition if specified
        if price is not None:
            if action == 'buy' and market_price > price:
                reason = f"Market price ({market_price:.2f}) > Limit price ({price:.2f})"
                dbg_warning(f"Buy order for {symbol} rejected: {reason}")
                return None
            elif action == 'sell' and market_price < price:
                reason = f"Market price ({market_price:.2f}) < Limit price ({price:.2f})"
                dbg_warning(f"Sell order for {symbol} rejected: {reason}")
                return None
            dbg_debug(f"Limit price condition met for {action} {symbol}: Market Price {market_price:.2f} vs Limit {price:.2f}")
        else:
            dbg_debug(f"Processing as market order for {action} {symbol} at Market Price {market_price:.2f}")


        # --- Execution Logic (uses market_price for calculations) ---
        cost = market_price * size # Cost/Proceeds based on actual market price
        commission = self.commission_rate * cost

        dbg_debug(f"Attempting {action} order: {symbol}, Size: {size}, Execution Price: {market_price:.2f}, Cost/Proceeds: {cost:.2f}, Commission: {commission:.2f}")

        if action == 'buy':
            required_cash = cost + commission
            if self.cash < required_cash:
                dbg_warning(f"Order rejected for {symbol}: Insufficient cash. Required: ${required_cash:.2f}, Available: ${self.cash:.2f}")
                # Create an MockOrder object to report the filled order
                order_instance = MockOrder(
                    event_type=Event.OrderFailed,
                    timestamp=datetime.now(),
                    symbol=symbol,
                    action=action,
                    size=size,
                    price=market_price, # Actual execution price
                    commission=commission,
                    status='failed', # Always filled in this mock
                    reason=f"Insufficient cash. Required: ${required_cash:.2f}, Available: ${self.cash:.2f}"
                )
                order_tracker = self._create_order_tracker(order_instance)
                self.update_order_status(order_tracker) # Call update_order_status to "update" the tracker
                return order_tracker

            # Update cash
            self.cash -= required_cash
            dbg_debug(f"Cash updated after BUY: ${self.cash:.2f}")

            # Update position
            if symbol not in self.positions:
                self.positions[symbol] = Position(symbol)
            self.positions[symbol].update(action, size, market_price) # Use market_price here
            # self._state_changed = True
            self._save_state() # Save state using the configured filepath
            dbg_info(f"Executed BUY: {symbol}, Size: {size}, Price: {market_price:.2f}. New Position: {self.positions[symbol]}")

        elif action == 'sell':
            current_position = self.get_position_by_symbol(symbol)
            if current_position.size < size:
                dbg_warning(f"Order rejected for {symbol}: Insufficient position to sell. Required: {size}, Available: {current_position.size}")
                # Create an MockOrder object to report the filled order
                order_instance = MockOrder(
                    event_type=Event.OrderFailed,
                    timestamp=datetime.now(),
                    symbol=symbol,
                    action=action,
                    size=size,
                    price=market_price, # Actual execution price
                    commission=commission,
                    status='failed', # Always filled in this mock
                    reason="Insufficient position to sell."
                )
                order_tracker = self._create_order_tracker(order_instance)
                self.update_order_status(order_tracker) # Call update_order_status to "update" the tracker
                return order_tracker

            # Update cash
            proceeds = cost
            self.cash += (proceeds - commission)
            dbg_debug(f"Cash updated after SELL: ${self.cash:.2f}")

            # Update position
            self.positions[symbol].update(action, size, market_price) # Use market_price here
            # self._state_changed = True
            self._save_state() # Save state using the configured filepath
            dbg_info(f"Executed SELL: {symbol}, Size: {size}, Price: {market_price:.2f}. New Position: {self.positions[symbol]}")

            # Clean up position if size becomes zero
            if self.positions[symbol].size == 0:
                dbg_debug(f"Position closed for {symbol}. Removing from holdings.")
                del self.positions[symbol]

        # Create an MockOrder object to report the filled order
        order_instance = MockOrder(
            event_type=Event.OrderFilled,
            timestamp=datetime.now(),
            symbol=symbol,
            action=action,
            size=size,
            price=market_price, # Actual execution price
            commission=commission,
            status='filled', # Always filled in this mock
            reason=None,
        )
        order_tracker = self._create_order_tracker(order_instance)
        self.update_order_status(order_tracker) # Call update_order_status to "update" the tracker

        return order_tracker

    def get_balance(self) -> float:
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
            return self.data_provider.get_current_price(symbol)
            # result_df = self.market.get_data(symbol)
            # if result_df is not None and not result_df.empty:
            #     # Assuming the DataFrame is sorted chronologically (latest date last)
            #     # and has a 'Close' column.
            #     last_price = result_df['Close'].iloc[-1]
            #     dbg_debug(f"Retrieved last price for {symbol}: {last_price}")
            #     return float(last_price) # Ensure it's a float
            # else:
            #     dbg_warning(f"Could not get last price for {symbol}: No data returned or DataFrame is empty.")
            #     return 0.0 # Return 0.0 if no data is available
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
        dbg_trace(f"Broker state file path set to: {self.state_filepath}")

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
            dbg_trace(f"Broker state saved successfully to {save_path}")
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
            dbg_trace(f"Broker state loaded successfully from {load_path}. Cash: ${self.cash:,.2f}, Positions: {len(self.positions)}")

        except (IOError, json.JSONDecodeError, KeyError, TypeError) as e:
            dbg_error(f"Failed to load or parse broker state from {load_path}: {e}. Using existing/default state.")
            # Decide how to handle errors: keep current state, reset, or raise exception
    def connect(self):
        """
        Connects the simulated broker. For MockBroker, this means loading the last saved state.
        """
        dbg_trace(f"Connecting MockBroker: Loading state from {self.state_filepath}...")
        self._load_state() # Load state using the configured filepath

    def disconnect(self):
        """
        Disconnects the simulated broker. For MockBroker, this means saving the current state
        if it has changed since the last load or save.
        """
        # We save it immediately in to file.
        # if self._state_changed:
        #     dbg_trace(f"Disconnecting MockBroker: State changed, saving state to {self.state_filepath}...")
        #     self._save_state() # Save state using the configured filepath
        # else:
        #     dbg_trace(f"Disconnecting MockBroker: State unchanged since last load/save, skipping save to {self.state_filepath}.")
        pass

