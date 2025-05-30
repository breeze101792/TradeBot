
import traceback
import datetime as dt
from datetime import date, time # Import date for tracking open date
from dotenv import load_dotenv
import os
# from queue import Queue
import queue
import shioaji as sj
# from shioaji import TickSTKv1

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
        ## Predefine of trading.
        self.simulation=simulation
        # if lot_trading is false, allow trading under 1 lot(meaning trading with value under 1000)
        self._is_lot_trade = False
        # get_last_price/place_order is depends on this flag.

        ## class variable.
        self.shioaji_api = None

        ## post-init of loading keys and other envs.
        cfgmgr = AppConfigManager()
        self._shioaji_env_root = os.path.join(os.path.expanduser(cfgmgr.get_path('key')), 'shioaji/shioaji_test.env')

        ## Sanity check.
        if self.simulation is False or (cfgmgr.get('debug.development') is True and self.simulation is False):
            dbg_error("We don't support real trade now.")
            raise NotImplementedError

        # Subclasses will initialize cash, positions, market data providers, etc.

    def is_connected(self):
        if self.shioaji_api == None:
            return False
        else:
            return True
    def is_lot_trade(self):
        return self._is_lot_trade

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
        if self.is_connected():
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

    def get_cash(self) -> float:
        #FIXME, rename to get_balance
        """
        Abstract method to return the current available cash balance in the broker account.

        Returns:
            float: The current cash balance.
        """
        if not self.is_connected():
            dbg_warning("Accound not connected.")
            return False

        balance = 0.0
        try:
            balance_result = self.shioaji_api.account_balance()
            balance = float(balance_result.acc_balance)
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

    def get_all_positions(self) -> dict[str, Position]:
        """
        Abstract method to return a dictionary of all current stock positions held by the broker.

        Returns:
            dict[str, Position]: A dictionary where keys are stock symbols (str)
                                 and values are Position objects.
                                 Example: `{'2330': Position(...), '2454': Position(...)}`
        """
        # self.shioaji_api.list_positions(self.shioaji_api.stock_account)
        # Return data structure.
        # [
        #     StockPosition(
        #         id=0, 
        #         code='2890', 
        #         direction=<Action.Buy: 'Buy'>, 
        #         quantity=12, 
        #         price=2.79, 
        #         last_price=16.95, 
        #         pnl=169171.0, 
        #         yd_quantity=12, 
        #         margin_purchase_amount=0, 
        #         collateral=0, 
        #         short_sale_margin=0, 
        #         interest=0
        #     )
        # ]
        if not self.is_connected():
            dbg_warning("Account not connected. Cannot fetch positions.")
            return {}

        positions = {}
        try:
            # Assuming stock_account is the first account in the list returned by login
            # Or, more robustly, iterate through self.shioaji_api.accounts if multiple
            # For simplicity, let's assume self.shioaji_api.stock_account is correctly set after login
            shioaji_positions = self.shioaji_api.list_positions(self.shioaji_api.stock_account)

            for sj_pos in shioaji_positions:
                # Ensure quantity is positive for held positions.
                if sj_pos.quantity > 0:
                    symbol = sj_pos.code
                    size = sj_pos.quantity
                    average_entry_price = sj_pos.price # This is the cost price from Shioaji

                    # Create a Position object.
                    # For initial_entry_price, we use average_entry_price as Shioaji doesn't provide a separate initial price.
                    # For open_date, Shioaji's list_positions doesn't provide it directly, so initialize to None.
                    position = Position(
                        symbol=symbol,
                        size=size,
                        average_entry_price=average_entry_price,
                        initial_entry_price=average_entry_price, # Use average as initial if not separately provided
                        open_date=None # Shioaji doesn't provide this directly in list_positions
                    )
                    positions[symbol] = position
                else:
                    dbg_info(f"Skipping position with zero or negative quantity: {sj_pos}")

        except Exception as e:
            dbg_error(f"Error fetching positions from Shioaji: {e}")
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return {} # Return empty dict on error

        return positions

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
        all_positions = self.get_all_positions()
        if symbol in all_positions:
            return all_positions[symbol]
        else:
            # If the symbol is not held, return a Position object with zero holdings
            return Position(symbol=symbol, size=0, average_entry_price=0.0, initial_entry_price=0.0, open_date=None)

    def get_portfolio_value(self) -> float:
        """
        Calculates the total value of the portfolio, including cash balance and the
        aggregate market value of all held stock positions. This implementation
        directly uses the `last_price` available in Shioaji's position objects.

        Returns:
            float: The total estimated value of the portfolio.
        """
        total_value = 0.0

        if not self.is_connected():
            dbg_warning("Account not connected. Cannot fetch positions for portfolio value.")
            return total_value # Return cash balance if not connected

        # 1. Get current cash balance
        cash_balance = self.get_cash()
        total_value += cash_balance
        dbg_debug(f"Current cash balance: {cash_balance:.2f}")

        try:
            # Directly get raw Shioaji positions to access last_price
            shioaji_positions = self.shioaji_api.list_positions(self.shioaji_api.stock_account)
            dbg_debug(f"Found {len(shioaji_positions)} raw Shioaji positions.")

            # 2. Calculate the market value of each position
            for sj_pos in shioaji_positions:
                # Ensure quantity is positive for held positions.
                if sj_pos.quantity > 0:
                    symbol = sj_pos.code
                    size = sj_pos.quantity
                    last_price = sj_pos.last_price # Use last_price directly from Shioaji StockPosition

                    if last_price is not None and last_price > 0:
                        position_market_value = size * last_price
                        total_value += position_market_value
                        dbg_debug(f"  Position {symbol}: Size={size}, Last Price={last_price:.2f}, Market Value={position_market_value:.2f}")
                    else:
                        dbg_warning(f"  Invalid last price ({last_price}) for {symbol}. Skipping its market value calculation.")
                else:
                    dbg_info(f"Skipping position with zero or negative quantity: {sj_pos.code}")

        except Exception as e:
            dbg_error(f"Error fetching positions for portfolio value from Shioaji: {e}")
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            # Return the total value calculated so far (at least cash) in case of error
            return total_value

        dbg_debug(f"Total portfolio value: {total_value:.2f}")
        return total_value

    def __get_last_price_odd(self, symbol: str) -> float:
        timeout=3
        tick_queue = queue.Queue()
        last_price = 0.0

        if not self.is_connected():
            dbg_warning("Account not connected. Cannot fetch positions for portfolio value.")
            return total_value # Return cash balance if not connected

        def quote_callback_quote(exchange: sj.Exchange, tick:sj.TickSTKv1):
            print(f"Exchange: {exchange}, Quote: {quote}")
            if quote.code == symbol:
                tick_queue.put(quote)

        try:
            # self.shioaji_api.set_quote_callback(tick_cb)
            self.shioaji_api.quote.set_on_quote_stk_v1_callback(quote_callback_quote)

            # fetch contracts, it may already fetched.
            self.shioaji_api.fetch_contracts(contract_download=True)

            # Find the stock contract (common for full and odd lots)
            contract = self.shioaji_api.Contracts.Stocks[symbol]

            # Subscribe to odd lot quotes
            self.shioaji_api.quote.subscribe(
                contract=contract,
                quote_type=sj.constant.QuoteType.Tick,
                intraday_odd=True,
                version=sj.constant.QuoteVersion.v1
            )

            # Attempt to get the first data point
            msg = tick_queue.get(timeout=timeout)
            # return {
            #     "symbol": msg.code,
            #     "price": msg.close,
            #     "volume": msg.volume,
            #     "tick_type": msg.tick_type,
            #     "time": f"{msg.datetime.time()}"
            # }
            last_price = float(msg.close)
        except queue.Empty:
            dbg_debug(f'[{symbol}] tick get empty.')
            last_price = 0.0
        except Exception as e:
            dbg_warning(e)
        
            traceback_output = traceback.format_exc()
            dbg_warning(traceback_output)
        finally:
            # Automatically unsubscribe after completion
            self.shioaji_api.quote.unsubscribe(
                contract=contract,
                quote_type=sj.constant.QuoteType.Tick,
                intraday_odd=True
            )
        return last_price

    def __place_order_odd(self, symbol: str, action: str, size: int, price: float | None = None) -> dict | None:
        """
        Places an odd lot order (buy or sell) for a given stock symbol.
        Assumes immediate filling for the purpose of this base broker.
        """
        if not self.is_connected():
            dbg_warning("Account not connected. Cannot place odd lot order.")
            return None

        if size <= 0:
            dbg_error(f"Invalid odd lot order size: {size}. Must be positive.")
            return None

        try:
            self.shioaji_api.fetch_contracts(contract_download=True)

            contract = self.shioaji_api.Contracts.Stocks[symbol]
            if not contract:
                dbg_error(f"Contract for symbol {symbol} not found.")
                return None

            # Determine Shioaji Action type
            sj_action = None
            if action.lower() == 'buy':
                sj_action = sj.constant.Action.Buy
            elif action.lower() == 'sell':
                sj_action = sj.constant.Action.Sell
            else:
                dbg_error(f"Invalid action: {action}. Must be 'buy' or 'sell'.")
                return None

            # Determine Shioaji PriceType
            # sj_price_type = sj.constant.StockPriceType.LMT
            if price is None:
                price = self.get_last_price(symbol)

            # Create an OddLotOrder
            # order = sj.order.OddLotOrder(
            #     price=price,
            #     quantity=size,
            #     action=sj_action,
            #     price_type=sj_price_type,
            #     order_type=sj.constant.OrderType.ROD # Rest of Day for odd lots
            # )
            order = self.shioaji_api.Order(
                price=price,
                quantity=size,
                action=sj_action,
                price_type=sj.constant.StockPriceType.LMT,
                order_type=sj.constant.OrderType.ROD,
                order_lot=sj.constant.StockOrderLot.IntradayOdd, 
                account=self.shioaji_api.stock_account,
            )

            dbg_debug(f"Placing odd lot order: Symbol={symbol}, Action={action}, Size={size}, Price={price}")

            # Place the order
            # trade = self.shioaji_api.place_order(contract, order, self.shioaji_api.stock_account)
            #########################################
            # contract = self.shioaji_api.Contracts.Stocks.TSE.TSE0050
            # order = self.shioaji_api.Order(
            #     price=90,
            #     quantity=10,
            #     action=sj.constant.Action.Buy,
            #     price_type=sj.constant.StockPriceType.LMT,
            #     order_type=sj.constant.OrderType.ROD,     
            #     order_lot=sj.constant.StockOrderLot.IntradayOdd, 
            #     account=self.shioaji_api.stock_account,
            # )

            trade = self.shioaji_api.place_order(contract, order)
            print(trade)
            #########################################

            # For the purpose of this base broker, we assume immediate fill if the API accepts the order.
            # In a real-time scenario, you would monitor trade.status for 'Filled'.
            if trade and trade.status.status == 'Filled':
                filled_price = trade.deal_price
                filled_size = trade.deal_quantity
                dbg_info(f"Odd lot order filled: Symbol={symbol}, Action={action}, Filled Price={filled_price}, Filled Size={filled_size}")

                # Placeholder for commission calculation.
                # Actual commission rules (e.g., minimums, taxes) vary and might be different for odd lots.
                commission_rate = 0.001425 # 0.1425%
                calculated_commission = filled_price * filled_size * commission_rate
                # A common minimum commission for full lots is 20 TWD, but often waived for odd lots or very small trades.
                # For simplicity, we'll use the calculated value, or a small default if it's zero.
                commission = max(calculated_commission, 0.0) # Ensure non-negative

                # FIXME, Remove return, since not one know if this ok or not in this monent.
                # Maybe we use callback for it.
                return {
                    'symbol': symbol,
                    'action': action,
                    'price': filled_price,
                    'size': filled_size,
                    'commission': commission,
                    'status': 'filled'
                }
            else:
                dbg_warning(f"Odd lot order failed or not filled: Symbol={symbol}, Action={action}, Status={trade.status.status if trade else 'No Trade Object'}")
                return None

        except Exception as e:
            dbg_error(f"Error placing odd lot order for {symbol}: {e}")
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return None
    def __get_last_price_lot(self, symbol: str) -> float:
        raise NotImplementedError
    def __place_order_lot(self, symbol: str, action: str, size: int, price: float | None = None) -> dict | None:
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
        if self._is_lot_trade:
            return self.__get_last_price_lot(symbol)
        else:
            return self.__get_last_price_odd(symbol)

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
        if self._is_lot_trade:
            return self.__place_order_lot(symbol, action, size, price)
        else:
            return self.__place_order_odd(symbol, action, size, price)
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

