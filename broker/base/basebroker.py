import json
import os
import datetime as dt
from datetime import date, time # Import date for tracking open date
from utility.debug import *

from market.market import *
from market.provider.twse import *
from broker.base.position import Position

class BaseBroker:
    """
    An abstract base class (prototype) for a trading broker.
    This class defines the essential interface and common functionalities that any
    concrete broker implementation (e.g., a simulated broker for backtesting,
    or a real-time broker for live trading) should adhere to.

    It manages core concepts like cash balance, stock positions, and order execution.
    Subclasses must implement the abstract methods to provide specific logic
    for market interaction, state management, and trade execution.
    """
    def __init__(self, broker_path: str):
        """
        Initializes the base broker with a specified path for potential state management.
        Concrete implementations will extend this to initialize cash, positions,
        market data providers, and other specific attributes.

        Args:
            broker_path (str): A base path that concrete brokers can use for
                                storing state files or configuration.
        """
        self.broker_path = broker_path
        # Subclasses will initialize cash, positions, market data providers, etc.

    def connect(self):
        """
        Abstract method to establish a connection for the broker.
        For simulated brokers, this typically involves loading the last saved state.
        For real-time brokers, this would involve establishing API connections.
        """
        raise NotImplementedError

    def disconnect(self):
        """
        Abstract method to gracefully disconnect the broker.
        For simulated brokers, this typically involves saving the current state.
        For real-time brokers, this would involve closing API connections.
        """
        raise NotImplementedError

    def get_cash(self) -> float:
        """
        Abstract method to return the current available cash balance in the broker account.

        Returns:
            float: The current cash balance.
        """
        raise NotImplementedError

    def get_all_positions(self) -> dict[str, Position]:
        """
        Abstract method to return a dictionary of all current stock positions held by the broker.

        Returns:
            dict[str, Position]: A dictionary where keys are stock symbols (str)
                                 and values are Position objects.
                                 Example: `{'2330': Position(...), '2454': Position(...)}`
        """
        raise NotImplementedError

    def get_position_by_symbol(self, symbol: str) -> Position:
        """
        Abstract method to return the Position object for a given stock symbol.
        If the symbol is not currently held, it should return a Position object
        representing a zero holding for that symbol.

        Args:
            symbol (str): The stock symbol.

        Returns:
            Position: The Position object for the specified symbol.
                      Example: `Position(symbol='2330', size=10, average_entry_price=150.50)`
                      If not held: `Position(symbol='AAPL', size=0, average_entry_price=0.0)`
        """
        raise NotImplementedError

    def get_portfolio_value(self) -> float:
        """
        Abstract method to calculate the total value of the portfolio.
        This typically includes the current cash balance plus the aggregate
        market value of all held stock positions.

        Requires a concrete implementation of `get_last_price` for accurate valuation.

        Returns:
            float: The total estimated value of the portfolio.
        """
        raise NotImplementedError

    def get_last_price(self, symbol: str) -> float:
        """
        Abstract method to retrieve the last known market price for a given stock symbol.
        Concrete implementations will fetch this data from a market data source.

        Args:
            symbol (str): The stock symbol.

        Returns:
            float: The last traded price of the stock. Returns 0.0 or raises an
                   appropriate error if the price cannot be retrieved.
        """
        raise NotImplementedError

    def place_order(self, symbol: str, action: str, size: int, price: float | None = None) -> dict | None:
        """
        Abstract method to simulate placing and immediately filling an order.
        This method should handle order validation (e.g., sufficient cash/position, valid size/action),
        determine the execution price, update cash balance, and adjust stock positions.

        - If `price` is `None`, it's a market order filled at the current market price.
        - If `price` is specified, it acts as a limit order:
            - Buy: Executes only if `current_market_price <= price`.
            - Sell: Executes only if `current_market_price >= price`.
        Execution, if successful, always happens at the `current_market_price`.

        Args:
            symbol (str): The stock symbol (e.g., "2330").
            action (str): The type of order: 'buy' or 'sell'.
            size (int): The quantity of shares to trade (must be positive).
            price (float | None, optional): The limit price for the order. If None, it's a market order.

        Returns:
            dict | None:
                - A dictionary with execution details if the order is filled:
                  Example: `{'symbol': '2330', 'action': 'buy', 'price': 150.50, 'size': 10, 'commission': 4.95, 'status': 'filled'}`
                - `None` if the order is rejected (e.g., insufficient funds, market closed, limit condition not met).
        """
        raise NotImplementedError

