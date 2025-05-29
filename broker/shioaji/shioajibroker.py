
import traceback
import datetime as dt
from datetime import date, time # Import date for tracking open date
from dotenv import load_dotenv
import os
import shioaji as sj

from utility.debug import *
from core.config import AppConfigManager

from broker.base.basebroker import BaseBroker
from broker.base.position import Position

def format_bytes(size):
    """Converts bytes to a human-readable format (KB, MB, GB, etc.), handling negative values."""
    if size is None:
        return "N/A"
    if size == 0:
        return "0 B" # Handle zero case explicitly

    sign = "-" if size < 0 else ""
    size = abs(size)

    # Define the units and their corresponding byte values
    power = 2**10 # 1024
    n = 0
    power_labels = {0 : 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'} # Start label with 'B'

    # Find the appropriate unit
    while size >= power and n < len(power_labels) - 1:
        size /= power
        n += 1

    # Format the output, adding the sign back if needed
    return f"{sign}{size:.2f} {power_labels[n]}"

class ShioajiBroker(BaseBroker):
    """
    An abstract base class (prototype) for a trading broker.
    This class defines the essential interface and common functionalities that any
    concrete broker implementation (e.g., a simulated broker for backtesting,
    or a real-time broker for live trading) should adhere to.

    It manages core concepts like cash balance, stock positions, and order execution.
    Subclasses must implement the abstract methods to provide specific logic
    for market interaction, state management, and trade execution.
    """
    def __init__(self, simulation = True, **kargs):
        """
        Initializes the base broker with a specified path for potential state management.
        Concrete implementations will extend this to initialize cash, positions,
        market data providers, and other specific attributes.

        Args:
            broker_path (str): A base path that concrete brokers can use for
                                storing state files or configuration.
        """
        super().__init__(**kargs)
        self.simulation=simulation
        self.shioaji_api = None

        cfgmgr = AppConfigManager()
        self._shioaji_env_root = os.path.join(os.path.expanduser(cfgmgr.get_path('key')), 'shioaji/shioaji_test.env')

        # Subclasses will initialize cash, positions, market data providers, etc.

    def __is_connected(self):
        if self.shioaji_api == None:
            return False
        else:
            return True

    def connect(self):
        """
        Logs into the Shioaji API using credentials from environment variables,
        activates the CA certificate, and prints available accounts.

        Args:
            simulation (bool): Whether to connect to the simulation environment. Defaults to True.

        Returns:
            shioaji.Shioaji: The initialized and logged-in API object.
        """
        check=True
        if self.__is_connected():
            dbg_warning('Shioaji is connected.')
            return True

        try:
            load_dotenv(dotenv_path=self._shioaji_env_root)

            self.shioaji_api = sj.Shioaji(simulation=self.simulation) # Use the simulation parameter
            accounts = self.shioaji_api.login(
                api_key=os.environ["API_KEY"],
                secret_key=os.environ["SECRET_KEY"],
                fetch_contract=False,
            )
            self.__print_account(accounts)

            self.shioaji_api.activate_ca(
                ca_path=os.environ["CA_CERT_PATH"],
                ca_passwd=os.environ["CA_PASSWORD"],
            )

        except Exception as e:
            dbg_error(e)

            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)

            # for savty, logout when fail to connect.
            if self.shioaji_api is not None:
                self.shioaji_api.logout()
            return False
        finally:
            self.__show_usage()

            if check:
                usage_data = self.shioaji_api.usage()
                # Limit 500MB, so warn on 450
                if usage_data.remaining_bytes < 1024*1024 * 20:
                    dbg_error(f"!!! Block login.!!! Remaining bytes smaller then 20MB. {format_bytes(usage_data.remaining_bytes)}")
                    self.shioaji_api.logout()
                    return False
                elif usage_data.remaining_bytes < 1024*1024 * 50:
                    dbg_warning(f"Remaining bytes smaller then 50MB. {format_bytes(usage_data.remaining_bytes)}")
        dbg_debug("login and activate ca success")
        return True

    def disconnect(self):
        """
        Logs out of the Shioaji API.

        Args:
            api (shioaji.Shioaji): The API object to log out from.
        """
        if self.shioaji_api is not None:
            print("Logout Account.")
            self.shioaji_api.logout()
        else:
            dbg_warning('Shioaji is not connected.')

    def is_market_open(self) -> bool:
        """
        Abstract method to check if the trading market is currently open.
        Concrete implementations will define specific market hours and holidays.

        Returns:
            bool: True if the market is open, False otherwise.

        Example (from MockBroker for TWSE):
            - Returns True if current time is between 9:00 AM and 1:25 PM on weekdays.
            - Returns False on weekends or outside trading hours.
        """
        raise NotImplementedError

    def get_cash(self) -> float:
        """
        Abstract method to return the current available cash balance in the broker account.

        Returns:
            float: The current cash balance.
        """
        if not self.__is_connected():
            dbg_warning("Accound not connected.")
            return False

        balance = 0
        try:
            balance_result = self.shioaji_api.account_balance()
            balance = balance_result.acc_balance
            if balance_result.errmsg != "":
                dbg_info(f"Account Balance Status: {balance.status}")
                dbg_info(f"Account Balance: {balance.acc_balance}")
                dbg_info(f"Query Date: {balance.date}")
                dbg_info(f"Error Message: {balance.errmsg}")

            # status (FetchStatus): fetch status
            # acc_balance (float): account balance
            # date (str): query date
            # errmsg (str): error message
        except Exception as e:
            dbg_error(f"Exception: {e}")
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)

        return balance

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

    def get_all_positions(self) -> dict[str, Position]:
        """
        Abstract method to return a dictionary of all current stock positions held by the broker.

        Returns:
            dict[str, Position]: A dictionary where keys are stock symbols (str)
                                 and values are Position objects.
                                 Example: `{'2330': Position(...), '2454': Position(...)}`
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
    def __show_usage(self):
        try:
            print("Usage data:")
            usage_data = self.shioaji_api.usage()
            print(f"  Connections     : {usage_data.connections}")
            print(f"  Bytes Used      : {format_bytes(usage_data.bytes)}")
            print(f"  Byte Limit      : {format_bytes(usage_data.limit_bytes)}")
            print(f"  Remaining Bytes : {format_bytes(usage_data.remaining_bytes)}")
            print("--------------------")
        except Exception as e:
            print(f"An error occurred: {e}")
            traceback_output = traceback.format_exc()
            print(traceback_output)
    def __print_account(self, accounts):
        """
        Prints the details of each account in the provided list in a formatted manner.

        Args:
            accounts: A list of Shioaji account objects (e.g., StockAccount).
        """
        print("Available accounts:")
        # Available accounts: [StockAccount(person_id='XXXXXXXX', broker_id='XXXX', account_id='XXXXX', signed=True, username='XXX'),]
        for account in accounts:
            print(f"  Person ID  : {getattr(account, 'person_id', 'N/A')}") # Use getattr for potential different account types
            print(f"  Broker ID  : {getattr(account, 'broker_id', 'N/A')}")
            print(f"  Account ID : {getattr(account, 'account_id', 'N/A')}")
            print(f"  Signed     : {getattr(account, 'signed', 'N/A')}")
            print(f"  Username   : {getattr(account, 'username', 'N/A')}")
            print("-" * 20) # Separator for multiple accounts

