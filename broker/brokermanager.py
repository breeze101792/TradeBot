
import traceback
from typing import Type, Dict, Any, Optional, List
import os
import csv
from datetime import datetime, timedelta
from collections import defaultdict # Import defaultdict
from tabulate import tabulate # Import tabulate for creating tables
import time # Import time for delays
import threading # Import threading for locks
import inspect

# Local file
from utility.debug import * # Replace standard logging with custom debug system
from core.config import AppConfigManager

# Assuming MockBroker is the primary implementation for now
from broker.brokers.base.position import Position
from broker.brokers.base.basebroker import BaseBroker
from broker.brokers.mock.mockbroker import MockBroker
from broker.brokers.shioaji.shioajibroker import ShioajiBroker

from broker.order.event import Event
from broker.order.orderservice import OrderService
from broker.order.ordertracker import OrderTracker
from broker.order.constant import OrderStatus, OrderAction, OrderPrice
from broker.transaction import TransactionManager

def event_callback(event: Event, data: Optional[Any] = None):
    """
    Callback function for handling events from the OrderService.
    This method processes different types of order-related events (e.g., OrderFilled, OrderFailed).

    Args:
        event (Event): The type of event that occurred.
        data (Optional[Any]): The data associated with the event, typically an `OrderTracker` object.
    """

    if BrokerManager.order_callback is not None:
        BrokerManager.order_callback(event, data)

    if event == Event.OrderFilled:
        if not isinstance(data, OrderTracker):
            dbg_error(f"Event '{event}' received with invalid data type. Expected OrderTracker, got {type(data)}.")
            return

        # Data is an OrderTracker object
        order_tracker: OrderTracker = data

        order_tracker.show_order()
        dbg_info(f"Order Filled: Symbol={order_tracker.symbol}, Action={order_tracker.action}, "
                 f"Size={order_tracker.size}, Price={order_tracker.price}, Commission={order_tracker.commission}.")

        bm = BrokerManager()
        # Log the transaction using data from the OrderTracker
        BrokerManager.transaction_mgr.log_transaction(
            symbol=order_tracker.symbol,
            action=order_tracker.action.value, # Use the string value of the enum
            size=order_tracker.size,
            price=order_tracker.price,
            commission=order_tracker.commission,
            cash_balance=bm.get_balance() # Get current balance after the transaction
        )
    elif event == Event.OrderFailed:
        if not isinstance(data, OrderTracker):
            dbg_error(f"Event '{event}' received with invalid data type. Expected OrderTracker, got {type(data)}.")
            return
        order_tracker: OrderTracker = data
        dbg_warning(f"Order Failed: Symbol={order_tracker.symbol}, Action={order_tracker.action}, "
                    f"Size={order_tracker.size}, Reason={order_tracker.reason}.")
        # Optionally log failed orders or take other actions
    elif event == Event.OrderPending:
        if not isinstance(data, OrderTracker):
            dbg_error(f"Event '{event}' received with invalid data type. Expected OrderTracker, got {type(data)}.")
            return
        order_tracker: OrderTracker = data
        dbg_info(f"Order Pending: Symbol={order_tracker.symbol}, Action={order_tracker.action}, "
                    f"Size={order_tracker.size}, Price={order_tracker.price}.")
    elif event == Event.OrderCanceled:
        if not isinstance(data, OrderTracker):
            dbg_error(f"Event '{event}' received with invalid data type. Expected OrderTracker, got {type(data)}.")
            return
        order_tracker: OrderTracker = data
        dbg_info(f"Order Canceled: Symbol={order_tracker.symbol}, Order ID={order_tracker.order_id}, "
                    f"Reason={order_tracker.reason}.")
    else:
        dbg_info(f"Unhandled event received: {event}, data: {data}")


class BrokerManager:
    """
    Manages different broker implementations, providing a unified interface.
    Acts as a wrapper around a specific broker instance.
    """
    # broker: BaseBroker = None
    # order_svc: OrderService = None
    broker = None
    order_svc = None
    transaction_mgr = None
    _broker_connected = False
    _lock = threading.Lock() # Class-level lock for thread safety
    order_callback = None
    broker_path = None

    def __init__(self):
        """
        Initializes the BrokerManager.
        Note: The actual broker and order service initialization is handled by the `initialize` class method.
        """
        self.cm = AppConfigManager()

    def set_order_callback(self, callback):
        BrokerManager.order_callback = callback

    def is_connected(self) -> bool:
        """
        Checks if the BrokerManager has been successfully initialized with a broker and order service.

        Returns:
            bool: True if initialized, False otherwise.
        """
        if BrokerManager.broker is not None and BrokerManager.order_svc is not None and BrokerManager._broker_connected is True:
            return True
        else:
            return False
    def lock(self, timeout: float = 10.0) -> bool:
        """
        Acquires the class-level lock with a timeout.
        Also checks broker quota after acquiring the lock.

        Args:
            timeout (float): The maximum time in seconds to wait for the lock.

        Returns:
            bool: True if the lock was acquired and quota check passed, False otherwise.
        """
        caller_frame = inspect.stack()[2]
        caller_filename = os.path.splitext(os.path.basename(caller_frame.filename))[0]
        caller_function = caller_frame.function
        caller_line_no = caller_frame.lineno

        dbg_trace(f'[{caller_filename}:{caller_function}@{caller_line_no}] Attempting to acquire lock with timeout {timeout}s...')

        if not BrokerManager._lock.acquire(timeout=timeout):
            dbg_error(f'[{caller_filename}:{caller_function}@{caller_line_no}] Failed to acquire lock within {timeout}s.')
            return False

        # Lock acquired, now check quota
        try:
            if BrokerManager.broker.check_quota() is False:
                dbg_error(f'[{caller_filename}:{caller_function}@{caller_line_no}] Quota check failed after acquiring lock.')
                BrokerManager._lock.release() # Release the lock if quota check fails
                return False
            else:
                dbg_trace(f'[{caller_filename}:{caller_function}@{caller_line_no}] Lock acquired and quota check passed.')
                return True
        except Exception as e:
            dbg_error(f'[{caller_filename}:{caller_function}@{caller_line_no}] Error during quota check: {e}')
            BrokerManager._lock.release() # Release the lock if an error occurs during quota check
            return False

    def unlock(self):
        """Releases the class-level lock."""
        BrokerManager._lock.release()
        caller_frame = inspect.stack()[2]
        caller_filename = os.path.splitext(os.path.basename(caller_frame.filename))[0]
        caller_function = caller_frame.function
        caller_line_no = caller_frame.lineno

        dbg_trace(f'[{caller_filename}:{caller_function}@{caller_line_no}] Unlock')

    @classmethod
    def reconnect(cls):
        sleep_delay = 60 * 10
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            dbg_info(f"Attempting to reconnect broker (Attempt {attempt}/{max_retries})...")
            cls._lock.acquire()
            try:
                if cls.broker is None: # Ensure broker exists before attempting disconnect
                    dbg_error(f"broker not found on {cls}.")
                    return False
                cls._broker_connected = False
                cls.broker.disconnect()
                time.sleep(5) # Wait before attempting to connect
                cls.broker.connect()
                cls._broker_connected = True
                dbg_info(f"Broker reconnected successfully on attempt {attempt}.")
                return True# Exit if successful
            except Exception as e:
                dbg_error(f"Reconnection attempt {attempt} failed: {e}")
                # Optionally log traceback for debugging
                # traceback_output = traceback.format_exc()
                # dbg_error(traceback_output)
                if attempt < max_retries:
                    dbg_info(f"Retrying in {sleep_delay} seconds...")
                    time.sleep(sleep_delay) # Wait before next retry
                else:
                    dbg_error(f"Failed to reconnect broker after {max_retries} attempts.")
                    # Re-raise the last exception if all attempts fail, or handle it as appropriate
                    return False# Exit if successful
            finally:
                cls._lock.release()
    @classmethod
    def initialize(cls, broker_type: str = 'mock', **kwargs: Any):
        """
        Initializes the BrokerManager's class-level broker and order service instances.
        This method should be called once before using any instance methods that rely on the broker.

        Args:
            broker_type (str): The type of broker to instantiate ('mock', 'shioaji', etc.). Defaults to 'mock'.
            **kwargs: Arguments to pass to the underlying broker's constructor.
                      - For 'mock': `initial_cash` (float), `commission_rate` (float), `simulation` (bool),
                                    `state_filepath` (str, for unit testing).
                      - For 'shioaji': `simulation` (bool).
                      - `transaction_log_path` (str): Optional path for the transaction log CSV.
        """
        cfg_mgr = AppConfigManager()
        # Predefine base on the broker type.
        # Init trasaction.
        transaction_log_path = kwargs.get('transaction_log_path', 
            os.path.join(cfg_mgr.get_path('broker'), f'{broker_type}/transactions.csv'))

        if cls.broker is not None:
            cls.broker.disconnect()

        # Init broker.
        if broker_type == 'mock':
            # Extract relevant kwargs for MockBroker, providing defaults if not present
            initial_cash = kwargs.get('initial_cash', 1000000.0)
            commission_rate = kwargs.get('commission_rate', 0.003)
            simulation = kwargs.get('simulation', False)
            BrokerManager.broker_path = os.path.join(cfg_mgr.get_path('broker'), f'{broker_type}')

            cls.broker = MockBroker(
                initial_cash=initial_cash,
                commission_rate=commission_rate,
                broker_path = BrokerManager.broker_path,
                simulation = simulation
            )
            # Set the state file path after initialization, this is for unitest.
            state_filepath = kwargs.get('state_filepath', "")
            if state_filepath != "":
                cls.broker.set_state_filepath(state_filepath)
            dbg_info(f"Initialized MockBroker via BrokerManager. Cash: ${initial_cash:,.2f}, Commission Rate: ${commission_rate:.2f}")
        elif broker_type == 'shioaji':
            # Extract relevant kwargs for ShioajiBroker, providing defaults if not present
            # Current we only enable simulation use.
            # simulation = kwargs.get('simulation', False)
            simulation = True
            BrokerManager.broker_path = os.path.join(cfg_mgr.get_path('broker'), f'{broker_type}')

            cls.broker = ShioajiBroker(
                broker_path = BrokerManager.broker_path,
                simulation = simulation
            )
            dbg_info(f"Initialized ShioajiBroker via BrokerManager.")
        # Add elif blocks here for other broker types in the future
        # elif broker_type == 'interactive_brokers':
        #     cls.broker = InteractiveBrokersBroker(**kwargs)
        else:
            dbg_error(f"Unsupported broker type: {broker_type}")
            raise ValueError(f"Unsupported broker type: {broker_type}")

        cls.transaction_mgr = TransactionManager(
            broker=cls.broker,
            lock=cls._lock,
            transaction_log_path=transaction_log_path
        )

        # Initialize OrderService with the broker instance for order tracking
        if cls.order_svc is not None:
            cls.order_svc.stop()

        cls.order_svc = OrderService(cls.broker, event_callback = event_callback)

        ## Post init
        cls.broker.connect()
        cls._broker_connected = True
        
        # get initial status if file not exist.
        cls.order_svc.start()
        dbg_info("inited.", cls.broker, cls.order_svc)

    @classmethod
    def finalize(cls):
        """
        Cleans up and disconnects the managed broker and stops the order service.
        This method should be called when the BrokerManager is no longer needed.
        """
        dbg_info("brokermanager finialized.")
        cls._lock.acquire()
        try:
            cls._broker_connected = False
            if cls.order_svc is not None:
                cls.order_svc.stop()
                cls.order_svc = None
            if cls.broker is not None:
                cls.broker.disconnect()
                cls.broker = None
        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
        finally:
            cls._lock.release()

    def place_order(self, symbol: str, action: OrderAction, size: int, price: Optional[float] = None) -> bool:
        """
        Places an order through the managed broker.

        Args:
            symbol (str): The stock symbol.
            action (OrderAction): `OrderAction.BUY` or `OrderAction.SELL`.
            size (int): The order quantity (must be positive).
            price (Optional[float]): The limit price. If None, the order is treated as a market order.
                                     For a buy order, it executes only if the market price is less than or equal to the limit price.
                                     For a sell order, it executes only if the market price is greater than or equal to the limit price.
                                     Execution, if successful, always happens at the current market price. Defaults to None.

        Returns:
            bool: True if the order was successfully placed and added to the order service, False otherwise.
        """
        if self.is_connected() is False:
            dbg_info('Please inited it first.')
            return False

        # it's backward compatible.
        if action in ['sell', 'SELL']:
            dbg_warning(f'Deprecated action({action}) detected, change it to use OrderAction.SELL')
            action = OrderAction.SELL
        elif action in ['buy', 'BUY']:
            dbg_warning(f'Deprecated action({action}) detected, change it to use OrderAction.BUY')
            action = OrderAction.BUY
        elif action not in [OrderAction.BUY, OrderAction.SELL]:
            reason = f"Invalid action '{action}'. Must be 'buy' or 'sell'."
            dbg_error(f"Order rejected for {symbol}: {reason}")
            raise ValueError
        if self.lock() is False:
            dbg_error(f"Lock acquire fail.")
            return False
        try:
            order = BrokerManager.broker.place_order(symbol, action, size, price)
        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return False
        finally:
            self.unlock()

        if order is not None:
            BrokerManager.order_svc.add_order(order)
            return True
        else:
            dbg_warning(f"Order not found.")
            return False

    def get_balance(self) -> float:
        """
        Returns the current available cash balance from the managed broker.

        Returns:
            float: The current cash balance.
        """
        if self.is_connected() is False:
            dbg_info('Please init it first.')
            return 0
        if self.lock() is False:
            dbg_error(f"Lock acquire fail.")
            return 0
        try:
            return BrokerManager.broker.get_balance()
        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
        finally:
            self.unlock()
        return 0

    def get_position_by_symbol(self, symbol: str) -> Position:
        """
        Returns the Position object for a given symbol from the managed broker.

        Args:
            symbol (str): The stock symbol.

        Returns:
            Position: The Position object for the symbol. If the symbol is not held,
                      returns a Position object with size 0 and default values.
        """
        if self.is_connected() is False:
            dbg_info('Please init it first.')
            return None
        if self.lock() is False:
            dbg_error(f"Lock acquire fail.")
            return None

        try:
            return BrokerManager.broker.get_position_by_symbol(symbol)
        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
        finally:
            self.unlock()

    def get_all_positions(self) -> Dict[str, Position]:
        """
        Returns a dictionary of all current positions from the managed broker.

        Returns:
            Dict[str, Position]: A dictionary where keys are symbols and values are `Position` objects.
        """
        if self.is_connected() is False:
            dbg_info('Please init it first.')
            return {}
        if self.lock() is False:
            dbg_error(f"Lock acquire fail.")
            return {}
        try:
            return BrokerManager.broker.get_all_positions()
        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
        finally:
            self.unlock()

    def get_last_price(self, symbol: str, price_type: OrderPrice) -> float:
        """
        Returns the last known market price for a symbol from the managed broker.

        Args:
            symbol (str): The stock symbol.
            price_type (OrderPrice): The type of price to retrieve (e.g., LAST, BID, ASK).

        Returns:
            float: The last known market price for the symbol.
        """
        if self.is_connected() is False:
            dbg_info('Please init it first.')
            return None
        if self.lock() is False:
            dbg_error(f"Lock acquire fail.")
            return None
        try:
            # Note: This might need adjustment if different brokers handle price fetching differently.
            return BrokerManager.broker.get_last_price(symbol, price_type)
        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
        finally:
            self.unlock()
        return None

    def get_portfolio_value(self) -> float:
        """
        Calculates the total value of the portfolio (cash + market value of positions)
        using the managed broker.

        Returns:
            float: The total portfolio value.
        """
        if self.is_connected() is False:
            dbg_info('Please init it first.')
            return 0
        if self.lock() is False:
            dbg_error(f"Lock acquire fail.")
            return 0
        try:
            return BrokerManager.broker.get_portfolio_value()
        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
        finally:
            self.unlock()

        return 0
    def set_state_filepath(self, filepath: str):
        """
        Sets the default file path for saving/loading state in the managed broker.
        This is primarily used for mock brokers or simulation environments.

        Args:
            filepath (str): The new default path for the state file.
        """
        if self.is_connected() is False:
            dbg_info('Please init it first.')
            raise ValueError
        BrokerManager.broker.set_state_filepath(filepath)

    def summarize_positions(self):
        """
        Prints a summary table of all current positions held by the managed broker.
        The summary includes details like size, average entry price, market value,
        and unrealized profit/loss for each symbol, along with portfolio totals.
        """
        if self.is_connected() is False:
            dbg_info('Please init it first.')
            raise ValueError
        cash = self.get_balance()
        positions = self.get_all_positions()
        if not positions:
            print("\n--- Current Positions Summary ---")
            print("No positions currently held.")
            
            # Match the way we print in Portfolio Totals
            print("\n--- Portfolio Totals ---")
            total_headers = ["Metric", "Value"]
            total_data = [
                ["Total Asset", f"${cash:,.2f}"], # If no positions, total asset is just cash
                ["Total Cash Value", f"${cash:,.2f}"]
            ]
            print(tabulate(total_data, headers=total_headers, tablefmt="grid", stralign="right"))
            return

        headers = [
            "Symbol", "Size", "Avg Entry", "Initial Entry", "Open Date",
            "Market Price", "Market Value", "Cost Basis", "Unrealized P/L", "Unrealized P/L %"
        ]
        table_data = []
        total_market_value = 0.0
        total_cost_basis = 0.0
        total_unrealized_pl = 0.0

        # dbg_info("Summarizing positions...")
        for symbol, pos in positions.items():
            try:
                current_price = self.get_last_price(symbol, OrderPrice.LAST)
                
                market_value_str = "N/A"
                cost_basis_str = "N/A"
                unrealized_pl_str = "N/A"
                unrealized_pl_percent_str = "N/A"
                current_price_str = "N/A"

                if current_price is not None and current_price > 0:
                    current_price_str = f"{current_price:,.2f}"
                    market_value = pos.size * current_price
                    cost_basis = pos.size * pos.average_entry_price
                    unrealized_pl = market_value - cost_basis
                    unrealized_pl_percent = (unrealized_pl / cost_basis * 100) if cost_basis != 0 else 0.0

                    # Add to totals ONLY if price is valid
                    total_market_value += market_value
                    total_cost_basis += cost_basis
                    total_unrealized_pl += unrealized_pl

                    market_value_str = f"{market_value:,.2f}"
                    cost_basis_str = f"{cost_basis:,.2f}"
                    unrealized_pl_str = f"{unrealized_pl:,.2f}"
                    unrealized_pl_percent_str = f"{unrealized_pl_percent:,.2f}%"
                else:
                    dbg_warning(f"Could not get valid market price for {symbol}. Calculations skipped for this position.")

                # Format data for the table row
                row = [
                    pos.symbol,
                    pos.size,
                    f"{pos.average_entry_price:,.2f}",
                    f"{pos.initial_entry_price:,.2f}",
                    pos.open_date.isoformat() if pos.open_date else 'N/A',
                    current_price_str,
                    market_value_str,
                    cost_basis_str,
                    unrealized_pl_str,
                    unrealized_pl_percent_str
                ]
                table_data.append(row)
                dbg_debug(f"Position Row Data for {symbol}: {row}")

            except Exception as e:
                dbg_error(f"Error processing position for {symbol}: {e}")
                # Add a row indicating an error for this symbol
                table_data.append([symbol, pos.size, 'Error', 'Error', 'Error', 'Error', 'Error', 'Error', 'Error', 'Error'])


        # Use tabulate to create the table string
        # Using 'grid' format for clear borders, 'floatfmt' for default float formatting (though we pre-format above)
        try:
            table_str = tabulate(table_data, headers=headers, tablefmt="grid", stralign="right")
            print("\n--- Current Positions Summary ---")
            print(table_str)

            # Print Totals
            # Print Totals in a table
            print("\n--- Portfolio Totals ---")
            total_headers = ["Metric", "Value"]
            total_asset = cash + total_market_value
            total_data = [
                ["Total Asset", f"${total_asset:,.2f}"], # New row for Total Asset
                ["Total Cash Value", f"${cash:,.2f}"],
                ["Total Market Value", f"${total_market_value:,.2f}"],
                ["Total Cost Basis", f"${total_cost_basis:,.2f}"],
                ["Total Unrealized P/L", f"${total_unrealized_pl:,.2f}"]
            ]
            print(tabulate(total_data, headers=total_headers, tablefmt="grid", stralign="right"))

        except Exception as e:
            dbg_error(f"Error generating position summary table with tabulate: {e}")
            print("\nError: Could not generate position summary table.")

    
    def get_transactions(self) -> List[Dict[str, Any]]:
        """
        Reads and returns all logged transactions from the CSV file.

        Returns:
            List[Dict[str, Any]]: A list of transaction records, where each record is a dictionary
                                  with keys matching the CSV headers (e.g., 'timestamp', 'symbol', 'action').
                                  Returns an empty list if the transaction log file does not exist.
        """
        if self.is_connected() is False:
            dbg_info('Please init it first.')
            raise ValueError
        return BrokerManager.transaction_mgr.get_transactions()

    def summarize_transactions(self, duration: Optional[str] = 'day'):
        """
        Prints a comprehensive summary of transactions, optionally filtered by a time duration.
        It includes overall transaction statistics and per-symbol details (buy/sell volume, P/L).
        If no transactions are found, it will display current positions as the initial state.

        Args:
            duration (Optional[str]): An optional filter for transactions.
                                      Accepted values: 'day', 'month', 'year', 'week'. Defaults to 'day'.
                                      If None, all historical transactions are summarized.
        """
        if self.is_connected() is False:
            dbg_info('Please init it first.')
            raise ValueError
        BrokerManager.transaction_mgr.summarize_transactions(duration)

    # You might add other broker-specific methods here as needed,

    # You might add other broker-specific methods here as needed,
    # potentially checking BrokerManager.broker_type if they aren't universal.

