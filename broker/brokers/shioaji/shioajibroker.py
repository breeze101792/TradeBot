
import traceback
import datetime as dt
from datetime import date, time, datetime # Import date and datetime for tracking open date and order events
from dotenv import load_dotenv
import os
# from queue import Queue
import queue
import shioaji as sj
# from shioaji import TickSTKv1
from tabulate import tabulate

from utility.debug import *
from utility.utils import format_bytes
from core.config import AppConfigManager

from broker.brokers.base.basebroker import BaseBroker
from broker.brokers.base.position import Position
from broker.order.ordertracker import OrderTracker
from broker.order.constant import OrderStatus, OrderAction, OrderPrice
from broker.order.event import Event
from broker.order.checker import OrderChecker

## TODO. 
"""
################################################################################
1. Add queme management for pulling tick data.
2. Add a reset for daily cash, may be add a class for cash management.
################################################################################
"""

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

        # cash manager.
        cfgmgr = AppConfigManager()
        self.cash_limit_per_trade = cfgmgr.get('stock.cash_max_per_trade') * 1.1
        self.daily_cash_limit = cfgmgr.get('stock.cash_max_per_trade') * 5
        self.daily_cash_amount = 0

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

    def check_quota(self):
        try:
            usage_data = self.shioaji_api.usage()
            # Limit 500MB, so warn on 450
            if usage_data.remaining_bytes < 1024*1024 * 20:
                dbg_error(f"!!! Block login.!!! Remaining bytes smaller then 20MB. {format_bytes(usage_data.remaining_bytes)}")
                return False
            elif usage_data.remaining_bytes < 1024*1024 * 50:
                dbg_warning(f"Remaining bytes smaller then 50MB. {format_bytes(usage_data.remaining_bytes)}")
                return True
        except Exception as e:
            dbg_error(e)
        
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return False
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

            if check and self.check_quota() is False:
                dbg_error(f"!!! Hit quota limit, block login.!!!")
                self.shioaji_api.logout()
                return False
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

    def get_balance(self) -> float:
        #FIXME, rename to get_balance
        """
        Abstract method to return the current available cash balance in the broker account.

        Returns:
            float: The current cash balance.
        """
        if not self.is_connected():
            dbg_warning("Accound not connected.")
            return False
        if self.simulation is True:
            dbg_info(f"Simulation mode, faking account balance.")
            return 10000

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
        cash_balance = self.get_balance()
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

    def _map_shioaji_action_to_orderaction(self, sj_action: sj.constant.Action) -> OrderAction:
        if sj_action == sj.constant.Action.Buy:
            return OrderAction.BUY
        elif sj_action == sj.constant.Action.Sell:
            return OrderAction.SELL
        return OrderAction.UNKNOWN # Or raise an error

    def _map_shioaji_status_to_orderstatus(self, sj_status: sj.constant.Status) -> OrderStatus:
        if sj_status == sj.constant.Status.Filled:
            return OrderStatus.FILLED
        elif sj_status == sj.constant.Status.PartFilled:
            return OrderStatus.PARTIALLY_FILLED
        elif sj_status == sj.constant.Status.Cancelled:
            return OrderStatus.CANCELLED
        elif sj_status == sj.constant.Status.PendingSubmit:
            return OrderStatus.PENDING_SUBMIT
        elif sj_status == sj.constant.Status.PreSubmitted:
            return OrderStatus.PRE_SUBMITTED
        elif sj_status == sj.constant.Status.Submitted:
            return OrderStatus.SUBMITTED
        elif sj_status == sj.constant.Status.Failed:
            return OrderStatus.REJECTED # Map Shioaji's Failed to REJECTED
        elif sj_status == sj.constant.Status.Expired:
            return OrderStatus.EXPIRED
        elif sj_status == sj.constant.Status.Rejected:
            return OrderStatus.REJECTED
        elif sj_status == sj.constant.Status.Inactive:
            return OrderStatus.INACTIVE
        return OrderStatus.UNKNOWN # Or raise an error

    def _create_order_tracker(self, trade: sj.order.Trade, event_type: Event, reason: str | None = None) -> OrderTracker:
        """
        Creates an OrderTracker instance from a Shioaji Trade object, linking the original trade.
        Initializes with basic info; full details are populated by update_order_status.
        """
        if not trade:
            dbg_error("Attempted to create OrderTracker from a None Shioaji Trade object.")
            return OrderTracker(
                timestamp=datetime.now(),
                symbol="UNKNOWN",
                action=OrderAction.UNKNOWN,
                size=0,
                price=0.0,
                commission=0.0,
                status=OrderStatus.FAILED,
                reason=reason if reason else "No Shioaji Trade object provided.",
                event_type=event_type
            )

        # Initial status based on the trade object's current status
        initial_status = self._map_shioaji_status_to_orderstatus(trade.status.status)

        tracker = OrderTracker(
            timestamp=trade.status.order_datetime if trade.status.order_datetime else datetime.now(),
            symbol=trade.contract.code,
            action=self._map_shioaji_action_to_orderaction(trade.order.action),
            size=trade.order.quantity, # Initial order quantity
            price=trade.order.price,   # Initial order price (limit price)
            commission=0.0,            # Commission calculated in update_order_status
            status=initial_status,
            reason=f"Tracker Created, status code: {trade.status.status_code}"
        )
        tracker.order_instance = trade # Link the original Shioaji Trade object
        return tracker

    def update_order_status(self, order_tracker: OrderTracker):
        """
        Updates the OrderTracker with the latest information from its internal Shioaji Trade instance.
        """
        trade = order_tracker.order_instance
        if not trade or not isinstance(trade, sj.order.Trade):
            dbg_warning("Cannot update OrderTracker: order_instance is missing or not a Shioaji Trade object.")
            return

        self.shioaji_api.update_status(trade=trade)
        # api.update_status(api.stock_account)
        # list trade and check?
        # api.list_trades()

        # Determine the executed price. If filled, use deal_price, otherwise order price.
        executed_price = trade.deal_price if trade.status.status == sj.constant.Status.Filled and trade.deal_price else trade.order.price
        executed_size = trade.deal_quantity if trade.status.status == sj.constant.Status.Filled and trade.deal_quantity else trade.order.quantity

        # Recalculate commission based on updated executed price and size
        # commission_rate = 0.001425 # 0.1425%
        # calculated_commission = executed_price * executed_size * commission_rate
        # commission = max(calculated_commission, 0.0) # Ensure non-negative
        # We didn't get commission on this broker.
        commission = 0

        order_tracker.timestamp = trade.status.order_datetime if trade.status.order_datetime else datetime.now()
        order_tracker.symbol = trade.contract.code
        order_tracker.action = self._map_shioaji_action_to_orderaction(trade.order.action)
        order_tracker.size = executed_size
        order_tracker.price = executed_price
        order_tracker.commission = commission
        order_tracker.status = self._map_shioaji_status_to_orderstatus(trade.status.status)
        order_tracker.reason = f"Status code: {trade.status.status_code}"
        dbg_debug(f"OrderTracker updated for {order_tracker.symbol} to status: {order_tracker.status.value}")

    def __get_last_price_odd(self, symbol: str, price_type: OrderPrice) -> float:
        timeout=3
        tick_queue = queue.Queue()
        last_price = 0.0

        if not self.is_connected():
            dbg_warning("Account not connected. Cannot fetch last price.")
            return 0.0 # Return 0.0 if not connected

        def tick_callback_quote(exchange: sj.Exchange, tick:sj.TickSTKv1): # Changed 'quote' to 'tick'
            print(f"Exchange: {exchange}, Tick: {tick}")
            if tick.code == symbol: # Changed 'quote.code' to 'tick.code'
                tick_queue.put(tick) # Changed 'quote' to 'tick'
            # code (str): 商品代碼
            # datetime (datetime): 時間
            # open (decimal): 開盤價
            # avg_price (decimal): 均價
            # close (decimal): 成交價
            # high (decimal): 最高價(自開盤)
            # low (decimal): 最低價(自開盤)
            # amount (decimal): 成交額 (NTD)
            # total_amount (decimal): 總成交額 (NTD)
            # volume (int): 成交量 (整股:張, 盤中零股: 股)
            # total_volume (int): 總成交量 (整股:張, 盤中零股: 股)
            # tick_type (int): 內外盤別{1: 外盤, 2: 內盤, 0: 無法判定}
            # chg_type (int): 漲跌註記{1: 漲停, 2: 漲, 3: 平盤, 4: 跌, 5: 跌停}
            # price_chg (decimal): 漲跌
            # pct_chg (decimal):  漲跌幅
            # bid_side_total_vol (int): 買盤成交總量 (整股:張, 盤中零股: 股)
            # ask_side_total_vol (int): 賣盤成交總量 (整股:張, 盤中零股: 股)
            # bid_side_total_cnt (int): 買盤成交筆數 
            # ask_side_total_cnt (int): 賣盤成交筆數 
            # closing_oddlot_shares (int): 盤後零股成交股數(股)   
            # fixed_trade_vol (int): 定盤成交量 (整股:張, 盤中零股: 股)
            # suspend (bool): 暫停交易
            # simtrade (bool): 試撮
            # intraday_odd (int): 盤中零股 {0: 整股, 1:盤中零股}

        contract = None # Initialize contract outside try block for finally
        try:
            # fetch contracts, it may already fetched.
            self.shioaji_api.fetch_contracts(contract_download=True)

            # FIXME, use quene to manger all request.
            self.shioaji_api.quote.set_on_tick_stk_v1_callback(tick_callback_quote)

            # Find the stock contract (common for full and odd lots)
            contract = self.shioaji_api.Contracts.Stocks[symbol]
            if not contract:
                dbg_warning(f"Contract for symbol {symbol} not found for price fetching.")
                return 0.0

            # Subscribe to odd lot quotes
            self.shioaji_api.quote.subscribe(
                contract=contract,
                quote_type=sj.constant.QuoteType.Tick,
                intraday_odd=True,
                version=sj.constant.QuoteVersion.v1
            )

            # Attempt to get the first data point
            tick_data = tick_queue.get(timeout=timeout)

            # NOTE. we don't have bid/ask price for shioaji, use close for it.
            # Determine which price to return based on price_type
            if tick_data.suspend is True:
                return float(0.0)
            else:
                last_price = float(tick_data.close)
        except queue.Empty:
            dbg_warning(f'[{symbol}] tick get empty. No price received within timeout.')
            last_price = 0.0
        except Exception as e:
            dbg_warning(f"Error fetching odd lot price for {symbol}: {e}")
            traceback_output = traceback.format_exc()
            dbg_warning(traceback_output)
            last_price = 0.0 # Ensure last_price is set to 0.0 on error
        finally:
            # Automatically unsubscribe after completion
            if contract: # Only unsubscribe if contract was successfully found
                self.shioaji_api.quote.unsubscribe(
                    contract=contract,
                    quote_type=sj.constant.QuoteType.Tick,
                    intraday_odd=True
                )
        return last_price

    def __place_order_odd(self, symbol: str, action: OrderAction, size: int, price: float | None = None) -> OrderTracker | None:
        """
        Places an odd lot order (buy or sell) for a given stock symbol.
        Assumes immediate filling for the purpose of this base broker.
        """
        # Determine OrderAction enum
        if action not in [OrderAction.SELL, OrderAction.BUY]:
            reason = f"Invalid odd lot action: {action}. Must be BUY/SELL."
            dbg_warning(reason)
            return None

        if size <= 0:
            reason = f"Invalid odd lot order size: {size}. Must be positive."
            dbg_error(reason)
            return None

        if not self.is_connected():
            reason = "Account not connected. Cannot place odd lot order."
            dbg_warning(reason)
            return None

        try:
            self.shioaji_api.fetch_contracts(contract_download=True)

            contract = self.shioaji_api.Contracts.Stocks[symbol]
            if not contract:
                reason = f"Contract for symbol {symbol} not found."
                dbg_error(reason)
                return None

            # Determine Shioaji Action type
            sj_action = None
            if action == OrderAction.BUY:
                sj_action = sj.constant.Action.Buy
            elif action == OrderAction.SELL:
                sj_action = sj.constant.Action.Sell
            else:
                reason = f"Invalid action: {action}. Must be 'buy' or 'sell'."
                dbg_error(reason)
            return None

            if price is None:
                price_type = OrderPrice.BID if action == OrderAction.SELL else OrderPrice.ASK
                current_market_price = self.get_last_price(symbol, price_type)
                if current_market_price <= 0:
                    reason = f"Could not get a valid market price for {symbol} to place order."
                    dbg_error(reason)
                    return None
                price = current_market_price

            # Sanity check
            ########################################################################
            # first sanity check
            if self.order_checker(action=action, price=price, size=size) is False:
                dbg_error(f"Check failed: {action.value} order: {symbol}, Size: {size}, Execution Price: {price:.2f}")
                return None

            # second sanity check
            if OrderChecker.check(action=action, price=price, size=size) is False:
                dbg_error(f"Check failed: {action.value} order: {symbol}, Size: {size}, Execution Price: {price:.2f}")
                return None
            ########################################################################

            # Create an OddLotOrder
            order = self.shioaji_api.Order(
                price=price,
                quantity=size,
                action=sj_action,
                price_type=sj.constant.StockPriceType.LMT, # Always use LMT for odd lots with a price
                order_type=sj.constant.OrderType.ROD,
                order_lot=sj.constant.StockOrderLot.IntradayOdd, 
                account=self.shioaji_api.stock_account,
            )

            # Place the order
            trade = self.shioaji_api.place_order(contract, order)
            self.__show_trade([trade]) # Pass as a list

            # update daily cash usage.
            if action == OrderAction.BUY:
                # TODO, reset by daily update.
                self.daily_cash_amount += size * price

            if trade and trade.status.status == sj.constant.Status.Filled:
                dbg_info(f"Odd lot order filled: Symbol={symbol}, Action={action}, Filled Price={trade.deal_price}, Filled Size={trade.deal_quantity}")
                order_tracker = self._create_order_tracker(trade, Event.OrderFilled)
                self.update_order_status(order_tracker) # Call update_order_status to populate full details
                return order_tracker
            else:
                if trade:
                    order_tracker = self._create_order_tracker(trade, Event.OrderFailed)
                    self.update_order_status(order_tracker) # Populate details for failed trade
                    return order_tracker
                else:
                    # Fallback if trade object itself is None (e.g., API call failed before returning trade)
                    reason = f"Odd lot order failed or not filled: Symbol={symbol}, Action={action}, Status={trade.status.status.value if trade else 'No Trade Object'}"
                    dbg_warning(reason)
                    return None

        except Exception as e:
            reason = f"Error placing odd lot order for {symbol}: {e}"
            dbg_error(reason)
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
            return None
    def __get_last_price_lot(self, symbol: str, price_type: OrderPrice) -> float:
        raise NotImplementedError
    def __place_order_lot(self, symbol: str, action: OrderAction, size: int, price: float | None = None) -> OrderTracker | None:
        raise NotImplementedError
    def get_last_price(self, symbol: str, price_type: OrderPrice) -> float:
        """
        Abstract method to retrieve the last known market price for a given stock symbol.
        Concrete implementations will fetch this data from a market data source.

        Args:
            symbol (str): The stock symbol.
            price_type (OrderPrice): The type of price to retrieve (e.g., LAST, BID, ASK).

        Returns:
            float: The last traded price of the stock. Returns 0.0 or raises an
                   appropriate error if the price cannot be retrieved.
        """
        if self._is_lot_trade:
            return self.__get_last_price_lot(symbol, price_type)
        else:
            return self.__get_last_price_odd(symbol, price_type)

    def order_checker(self, action, price, size) -> bool:
        """
        Abstract method to perform validation checks on order parameters (action, price, size).
        This method ensures that the provided order details are valid before attempting
        to place or process an order, preventing miscalculations or invalid trades.

        Args:
            action (OrderAction): The type of order (e.g., 'buy', 'sell').
            price (float): The price at which the order is intended to be executed.
            size (int): The quantity of shares for the order.

        Returns:
            bool: True if the order parameters pass the validation checks, False otherwise.
        """
        # update daily_cash_limit
        current_balance = self.get_balance()
        if current_balance < self.daily_cash_limit:
            dbg_warning('Account banalce({current_balance}) warning, it is lower then daily_cash_limit({self.daily_cash_limit}).')
            daily_limit = current_balance
        else:
            daily_limit = self.daily_cash_limit
        if action == OrderAction.BUY and self.daily_cash_amount + size * price > daily_limit:
            reason = f"order reject by daily cash checker, size: {size}, price:{price}, current: {self.daily_cash_amount},limit: {daily_limit}"
            dbg_error(reason)
            return False

        if action == OrderAction.BUY and price * size > self.cash_limit_per_trade:
            reason = f"order reject by size checker, size: {size}, price:{price}, current: {size * price},limit: {self.cash_limit_per_trade}"
            dbg_error(reason)
            return False

        # current we don't have check on this.
        # if action == OrderAction.SELL:
        #     pass
        return True
    def place_order(self, symbol: str, action: OrderAction, size: int, price: float | None = None) -> OrderTracker | None:
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
            OrderTracker | None:
                - An OrderTracker object with execution details if the order is filled or rejected.
                - `None` if a critical error prevents even creating a rejected tracker.
        """
        if self._is_lot_trade:
            return self.__place_order_lot(symbol, action, size, price)
        else:
            return self.__place_order_odd(symbol, action, size, price)

    def __show_trade(self, trades: list[sj.order.Trade]):
        """
        Displays trade details using tabulate, ignoring account information.
        Args:
            trades (list[sj.Trade]): A list of trade objects from Shioaji.
        """
        if not trades:
            dbg_warning("No trades to display.")
            return

        for i, trade in enumerate(trades):
            dbg_info(f"--- Trade Details ({i+1}/{len(trades)}) ---")
            # trade(<class 'shioaji.order.Trade'>): contract=Stock(exchange=<Exchange.TSE: 'TSE'>, code='2330', symbol='TSE2330', name='台積電', category='24', unit=1000, limit_up=1040.0, limit_down=852.0, reference=946.0, update_date='2025/06/03', margin_trading_balance=326, short_selling_balance=125, day_trade=<DayTrade.Yes: 'Yes'>) order=Order(action=<Action.Buy: 'Buy'>, price=1010, quantity=1, id='0006E5', seqno='0006E5', ordno='0001B9', account=Account(account_type=<AccountType.Stock: 'S'>, person_id='', broker_id='9A9P', account_id='0367021', signed=True), price_type=<StockPriceType.LMT: 'LMT'>, order_type=<OrderType.ROD: 'ROD'>, order_lot=<StockOrderLot.IntradayOdd: 'IntradayOdd'>) status=OrderStatus(id='0006E5', status=<Status.PendingSubmit: 'PendingSubmit'>, status_code='00', order_datetime=datetime.datetime(2025, 6, 3, 16, 17, 47, 306041), deals=[])

            contract = trade.contract
            order = trade.order
            status = trade.status

            trade_headers = [
                "Trade ID", "Symbol", "Name", "Action", "Order Price", "Order Quantity",
                "Order Type", "Price Type", "Order Lot", "Current Status", "Status Code", "Order Datetime"
            ]
            trade_values = [
                order.id,
                contract.code if contract else "N/A",
                contract.name if contract else "N/A",
                order.action.value if order.action else "N/A",
                order.price,
                order.quantity,
                order.order_type.value if order.order_type else "N/A",
                order.price_type.value if order.price_type else "N/A",
                order.order_lot.value if order.order_lot else "N/A",
                status.status.value if status.status else "N/A",
                status.status_code,
                status.order_datetime.strftime("%Y-%m-%d %H:%M:%S") if status.order_datetime else "N/A",
            ]
            print(tabulate([trade_values], headers=trade_headers, tablefmt="grid"))

            if status.deals:
                dbg_info("\n--- Deal Details ---")
                deal_headers = ["Deal Price", "Deal Quantity", "Deal Datetime"]
                deal_rows = []
                for deal in status.deals:
                    deal_rows.append([
                        deal.deal_price,
                        deal.deal_quantity,
                        deal.deal_datetime.strftime("%Y-%m-%d %H:%M:%S") if deal.deal_datetime else "N/A"
                    ])
                print(tabulate(deal_rows, headers=deal_headers, tablefmt="grid"))
            dbg_info("--------------------")

    def __show_usage(self):
        try:
            dbg_info("--- Usage Data ---")
            usage_data = self.shioaji_api.usage()
            usage_headers = ["Connections", "Bytes Used", "Byte Limit", "Remaining Bytes"]
            usage_values = [
                usage_data.connections,
                format_bytes(usage_data.bytes),
                format_bytes(usage_data.limit_bytes),
                format_bytes(usage_data.remaining_bytes),
            ]
            print(tabulate([usage_values], headers=usage_headers, tablefmt="grid"))
            dbg_info("--------------------")
        except Exception as e:
            dbg_error(f"An error occurred while fetching usage data: {e}")
            traceback_output = traceback.format_exc()
            dbg_error(traceback_output)
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

