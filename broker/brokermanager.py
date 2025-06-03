
from typing import Type, Dict, Any, Optional, List
import os
import csv
from datetime import datetime, timedelta
from collections import defaultdict # Import defaultdict
from tabulate import tabulate # Import tabulate for creating tables

# Local file
from utility.debug import * # Replace standard logging with custom debug system

# Assuming MockBroker is the primary implementation for now
from broker.mock.mockbroker import MockBroker, Position
from core.config import *

class BrokerManager:
    """
    Manages different broker implementations, providing a unified interface.
    Acts as a wrapper around a specific broker instance.
    """
    def __init__(self, broker_type: str = 'mock', **kwargs: Any):
        """
        Initializes the BrokerManager with a specific broker type.

        Args:
            broker_type (str): The type of broker to instantiate ('mock', etc.). Defaults to 'mock'.
            **kwargs: Arguments to pass to the underlying broker's constructor
                      (e.g., initial_cash, commission_rate, broker_path).
        """
        self.cm = AppConfigManager()
        self.broker: MockBroker # Type hint for the wrapped broker instance
        self.broker_type = broker_type

        self.transaction_log_path = kwargs.get('transaction_log_path', 
            os.path.join(self.cm.get_path('broker'), f'{broker_type}/transactions.csv'))
        self._ensure_transaction_log_dir()

        if broker_type == 'mock':
            # Extract relevant kwargs for MockBroker, providing defaults if not present
            initial_cash = kwargs.get('initial_cash', 1000000.0)
            commission_rate = kwargs.get('commission_rate', 0.003)
            simulation = kwargs.get('simulation', False)

            self.broker = MockBroker(
                initial_cash=initial_cash,
                commission_rate=commission_rate,
                broker_path = os.path.join(self.cm.get_path('broker'), f'{broker_type}'),
                simulation = simulation
            )
            # Set the state file path after initialization
            # self.broker.set_state_filepath(state_filepath)
            dbg_debug(f"Initialized MockBroker via BrokerManager. Cash: ${initial_cash:,.2f}, Commission: ${commission_rate:.2f}")
        elif broker_type == 'Shioaji':
            pass
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
            price (Optional[float]): The limit price. If None, the order is treated as a market order.
                                     For a buy order, it executes only if the market price is less than or equal to the limit price.
                                     For a sell order, it executes only if the market price is greater than or equal to the limit price.
                                     Execution, if successful, always happens at the current market price. Defaults to None.

        Returns:
            Optional[Dict[str, Any]]: Details of the execution, or None if rejected/failed.
        """
        result = self.broker.place_order(symbol, action, size, price)
        if result:
            self._log_transaction(
                symbol=symbol,
                action=action,
                size=size,
                price=result['price'],
                commission=result['commission'],
                cash_balance=self.get_balance()
            )
        return result

    def get_balance(self) -> float:
        """Returns the current available cash balance from the managed broker."""
        return self.broker.get_balance()

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
        cash = self.broker.get_balance()
        positions = self.broker.get_all_positions()
        if not positions:
            print("No positions currently held.")
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
                current_price = self.broker.get_last_price(symbol)
                if current_price <= 0:
                    dbg_warning(f"Could not get valid market price for {symbol}, using 0.0 for calculations.")
                    current_price = 0.0 # Handle case where price might be invalid

                market_value = pos.size * current_price
                cost_basis = pos.size * pos.average_entry_price
                unrealized_pl = market_value - cost_basis
                unrealized_pl_percent = (unrealized_pl / cost_basis * 100) if cost_basis != 0 else 0.0

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
                    f"{unrealized_pl:,.2f}",
                    f"{unrealized_pl_percent:,.2f}%"
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
            # Print Totals in a table
            print("\n--- Portfolio Totals ---")
            total_headers = ["Metric", "Value"]
            total_data = [
                ["Total Cash Value", f"${cash:,.2f}"],
                ["Total Market Value", f"${total_market_value:,.2f}"],
                ["Total Cost Basis", f"${total_cost_basis:,.2f}"],
                ["Total Unrealized P/L", f"${total_unrealized_pl:,.2f}"]
            ]
            print(tabulate(total_data, headers=total_headers, tablefmt="grid", stralign="right"))

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
            # get initial status if file not exist.
            self._log_transaction_init()
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

    def _ensure_transaction_log_dir(self):
        """Ensures the directory for transaction logs exists."""
        os.makedirs(os.path.dirname(self.transaction_log_path), exist_ok=True)

    def _log_transaction_init(self):
        log_exists = os.path.exists(self.transaction_log_path)
        now_iso = datetime.now().isoformat()

        # TODO, We didn't handle the transacion when the file arleady exist, but not done by this program.
        if not log_exists:
            # File doesn't exist, create it, log initial positions, then log the current transaction
            initial_positions = self.get_all_positions()
            cash_balance = self.get_balance()
            with open(self.transaction_log_path, 'w', newline='') as f:
                writer = csv.writer(f)
                # Write header
                header = ['timestamp', 'symbol', 'action', 'size', 'price', 'commission', 'cash_balance']
                writer.writerow(header)

                # Log existing positions as 'initial' state if any exist
                if initial_positions:
                    dbg_info(f"Transaction log not found. Logging {len(initial_positions)} initial positions.")
                    for pos_symbol, pos in initial_positions.items():
                        # Note: cash_balance here reflects the balance *after* the current transaction,
                        # not the balance when the initial position was established.
                        initial_row = [
                            now_iso, # Timestamp of when the log was created/initial state recorded
                            pos_symbol,
                            'initial', # Special action type
                            pos.size,
                            pos.average_entry_price,
                            0.0, # No commission for initial state logging
                            cash_balance # Use current cash balance
                        ]
                        writer.writerow(initial_row)

    def _log_transaction(self, symbol: str, action: str, size: int, price: float, 
                        commission: float, cash_balance: float):
        """
        Logs a transaction to the CSV file.
        
        Args:
            symbol: Trading symbol
            action: 'buy' or 'sell'
            size: Number of shares
            price: Execution price per share
            commission: Commission paid
            cash_balance: Cash balance after transaction
        """
        # log_exists = os.path.exists(self.transaction_log_path)
        now_iso = datetime.now().isoformat()

        self._log_transaction_init()

        # File exists, append the current transaction
        with open(self.transaction_log_path, 'a', newline='') as f:
            writer = csv.writer(f)
            current_transaction_row = [
                now_iso,
                symbol,
                action,
                size,
                price,
                commission,
                cash_balance
            ]
            writer.writerow(current_transaction_row)

    def get_transactions(self) -> List[Dict[str, Any]]:
        """
        Returns all logged transactions as a list of dictionaries.
        
        Returns:
            List of transaction records with keys matching CSV headers
        """
        if not os.path.exists(self.transaction_log_path):
            return []
            
        with open(self.transaction_log_path, 'r') as f:
            reader = csv.DictReader(f)
            return list(reader)

    def summarize_transactions(self, duration: str = None):
        """
        Prints a summary of transactions with additional stock status information.
        If no transactions are found, it will display current positions as the initial state.

        Args:
            duration (str): Optional filter for transactions ('month', 'year', 'week')
        """
        transactions = self.get_transactions()
        current_positions = self.get_all_positions()

        # Handle case where there are no transactions (potentially initial state from loaded positions)
        if not transactions:
            if not current_positions:
                print("No transactions recorded and no positions held.")
                return
            else:
                print("\n--- Transactions Summary (No History) ---")
                summary_data = [
                    ["Time Period", f"Initial State (No Transactions)"],
                    ["Total Transactions", 0],
                    ["Buy Orders", 0],
                    ["Sell Orders", 0],
                    ["Total Commission", "$0.00"],
                    ["Estimated Profit", "$0.00"]
                ]
                print(tabulate(summary_data, tablefmt="grid", stralign="right"))

                print("\n--- Stock Status (Initial) ---")
                stock_status_data = []
                for symbol, pos in current_positions.items():
                    try:
                        current_price = self.get_last_price(symbol)
                    except Exception:
                        current_price = 0.0 # Handle error fetching price
                    stock_status_data.append([
                        symbol,
                        "Open", # Mark as Open since it's a current holding
                        pos.size,
                        f"${pos.average_entry_price:,.2f}",
                        f"${current_price:,.2f}"
                    ])
                
                if stock_status_data:
                    print(tabulate(
                        stock_status_data,
                        headers=["Symbol", "Status", "Shares", "Avg Entry $", "Mkt Price"],
                        tablefmt="grid",
                        stralign="right"
                    ))
                else:
                    # This case should technically not be reached if current_positions is not empty
                    print("No current positions found despite initial check.")
                return # Stop processing as there are no transactions

        # --- Original logic continues below if transactions exist ---

        # Filter by duration if specified
        now = datetime.now()
        filtered_transactions = transactions # Start with all transactions
        if duration:
            if duration == 'month':
                cutoff = now - timedelta(days=30)
            elif duration == 'year':
                cutoff = now - timedelta(days=365)
            elif duration == 'week':
                cutoff = now - timedelta(days=7)
            else:
                raise ValueError("Invalid duration. Use 'month', 'year' or 'week'")
            
            filtered_transactions = [t for t in transactions 
                                     if datetime.fromisoformat(t['timestamp']) >= cutoff]

        if not filtered_transactions and not duration: # No transactions at all, and no duration filter
            print(f"No transactions found.")
            return
        
        # --- Calculate initial positions at cutoff_date if duration is set ---
        initial_positions_at_cutoff = defaultdict(lambda: {'size': 0, 'total_cost_basis': 0.0})
        pre_period_transactions_for_initial_state = []

        if duration and cutoff:
            # Prepare transactions for calculating initial state (up to and including cutoff)
            for t_data_raw in transactions: # Use original full list of transactions
                try:
                    t_timestamp = datetime.fromisoformat(t_data_raw['timestamp'])
                    if t_timestamp <= cutoff:
                        # Parse numerics here to avoid repeated parsing if transaction is used later
                        size_val, price_val, commission_val = self._parse_transaction_numerics(t_data_raw)
                        if size_val is None: continue # Skip malformed
                        
                        pre_period_transactions_for_initial_state.append({
                            'symbol': t_data_raw['symbol'],
                            'action': t_data_raw['action'],
                            'size': size_val,
                            'price': price_val,
                            'commission': commission_val,
                            'timestamp': t_timestamp # Already datetime object
                        })
                except ValueError as e:
                    dbg_error(f"Error parsing timestamp for transaction {t_data_raw}: {e}")
                    continue
            
            # Sort by timestamp to correctly build initial state
            pre_period_transactions_for_initial_state.sort(key=lambda x: x['timestamp'])

            for t_data in pre_period_transactions_for_initial_state:
                symbol = t_data['symbol']
                action = t_data['action']
                size = t_data['size']
                price = t_data['price']
                commission = t_data['commission']
                
                current_pos_state = initial_positions_at_cutoff[symbol]
                if action == 'buy' or action == 'initial':
                    cost_of_this_buy = (price * size) + commission
                    current_pos_state['total_cost_basis'] += cost_of_this_buy
                    current_pos_state['size'] += size
                elif action == 'sell':
                    if current_pos_state['size'] > 0:
                        avg_cost_per_share = current_pos_state['total_cost_basis'] / current_pos_state['size']
                        cost_basis_of_sold_shares = avg_cost_per_share * min(size, current_pos_state['size'])
                        current_pos_state['total_cost_basis'] -= cost_basis_of_sold_shares
                    current_pos_state['size'] -= size
                    current_pos_state['size'] = max(0, current_pos_state['size'])
                    if current_pos_state['size'] == 0:
                        current_pos_state['total_cost_basis'] = 0.0
        
        # Check if there's any data to show (either period transactions or initial positions)
        if not filtered_transactions and not any(p['size'] > 0 for p in initial_positions_at_cutoff.values()):
            print(f"No transactions or relevant initial positions for the specified period ('{duration}').")
            return

        # --- Aggregate data for symbols active in the period or at its start ---
        symbol_period_details = defaultdict(lambda: {
            'period_buy_volume': 0, 'period_buy_value': 0.0, 'period_buy_commissions': 0.0,
            'period_sell_volume': 0, 'period_sell_value': 0.0, 'period_sell_commissions': 0.0,
            'net_pnl_period': 0.0,
            'last_trade_timestamp_in_period': None
        })

        # Initialize P/L tracking with initial positions for the period
        # This pnl_tracking_state evolves *during* the period for accurate COGS
        pnl_tracking_state = defaultdict(lambda: {'current_size': 0, 'current_total_cost_basis': 0.0})

        if duration: # Populate with state at cutoff
            for symbol, data in initial_positions_at_cutoff.items():
                if data['size'] > 0:
                    pnl_tracking_state[symbol]['current_size'] = data['size']
                    pnl_tracking_state[symbol]['current_total_cost_basis'] = data['total_cost_basis']
                    # Ensure symbol appears in symbol_period_details if it has an initial position,
                    # so it's included in the table even with no period transactions.
                    _ = symbol_period_details[symbol] 
        
        # Process period transactions (transactions in `filtered_transactions`)
        # Ensure `filtered_transactions` are sorted by timestamp for correct P/L calculation
        # `filtered_transactions` already contains parsed numerics if we modify its creation
        
        # Re-parse or pre-parse filtered_transactions to include datetime objects and numeric types
        processed_period_transactions = []
        for t_data_raw in filtered_transactions:
            try:
                size_val, price_val, commission_val = self._parse_transaction_numerics(t_data_raw)
                if size_val is None: continue
                processed_period_transactions.append({
                    'symbol': t_data_raw['symbol'],
                    'action': t_data_raw['action'],
                    'size': size_val,
                    'price': price_val,
                    'commission': commission_val,
                    'timestamp': datetime.fromisoformat(t_data_raw['timestamp'])
                })
            except ValueError as e:
                dbg_error(f"Error parsing data for period transaction {t_data_raw}: {e}")
                continue
        
        processed_period_transactions.sort(key=lambda x: x['timestamp'])


        for t_data in processed_period_transactions:
            symbol = t_data['symbol']
            action = t_data['action']
            size = t_data['size']
            price = t_data['price']
            commission = t_data['commission']
            timestamp = t_data['timestamp']

            details = symbol_period_details[symbol]
            current_pnl_state = pnl_tracking_state[symbol]

            if action == 'buy' or action == 'initial': # 'initial' should ideally not be in period transactions
                details['period_buy_volume'] += size
                details['period_buy_value'] += price * size
                details['period_buy_commissions'] += commission
                
                cost_of_this_buy = (price * size) + commission
                current_pnl_state['current_total_cost_basis'] += cost_of_this_buy
                current_pnl_state['current_size'] += size
            
            elif action == 'sell':
                details['period_sell_volume'] += size
                details['period_sell_value'] += price * size
                details['period_sell_commissions'] += commission

                proceeds_this_sell = (price * size) - commission
                cost_of_goods_sold_this_sell = 0.0
                
                if current_pnl_state['current_size'] > 0:
                    avg_cost_at_sell_time = current_pnl_state['current_total_cost_basis'] / current_pnl_state['current_size']
                    # COGS is based on shares actually available to sell from current holding for P/L state
                    sold_size_for_cogs = min(size, current_pnl_state['current_size']) 
                    cost_of_goods_sold_this_sell = avg_cost_at_sell_time * sold_size_for_cogs
                
                pnl_this_sell = proceeds_this_sell - cost_of_goods_sold_this_sell
                details['net_pnl_period'] += pnl_this_sell
                
                current_pnl_state['current_total_cost_basis'] -= cost_of_goods_sold_this_sell
                current_pnl_state['current_size'] -= size # Actual size reduction from sell
                current_pnl_state['current_size'] = max(0, current_pnl_state['current_size'])
                if current_pnl_state['current_size'] == 0:
                    current_pnl_state['current_total_cost_basis'] = 0.0
            
            if details['last_trade_timestamp_in_period'] is None or timestamp > details['last_trade_timestamp_in_period']:
                details['last_trade_timestamp_in_period'] = timestamp

        # --- Calculate derived metrics for table and grand totals ---
        grand_total_net_pnl_period = 0.0
        per_symbol_table_data = []

        # Iterate over symbols that had initial positions or period activity
        active_symbols = set(initial_positions_at_cutoff.keys()) | set(s['symbol'] for s in processed_period_transactions)
        
        for symbol in sorted(list(active_symbols)): # Sort for consistent table order
            data = symbol_period_details[symbol] # Contains period transaction aggregates and P/L
            
            avg_buy_price_period = (data['period_buy_value'] / data['period_buy_volume']) if data['period_buy_volume'] > 0 else 0.0
            total_buy_cost_period_display = data['period_buy_value'] + data['period_buy_commissions']
            
            avg_sell_price_period = (data['period_sell_value'] / data['period_sell_volume']) if data['period_sell_volume'] > 0 else 0.0
            total_sell_income_period_display = data['period_sell_value'] - data['period_sell_commissions']
            
            net_volume_period = data['period_buy_volume'] - data['period_sell_volume']
            grand_total_net_pnl_period += data['net_pnl_period']
            
            last_trade_date_str = data['last_trade_timestamp_in_period'].strftime('%Y-%m-%d') if data['last_trade_timestamp_in_period'] else 'N/A'

            per_symbol_table_data.append([
                symbol,
                data['period_buy_volume'], f"${avg_buy_price_period:,.2f}", f"${total_buy_cost_period_display:,.2f}",
                data['period_sell_volume'], f"${avg_sell_price_period:,.2f}", f"${total_sell_income_period_display:,.2f}",
                net_volume_period,
                f"${data['net_pnl_period']:,.2f}",
                last_trade_date_str
            ])

        # Sort per_symbol_table_data by "Net Vol" (index 7) in descending order
        # x[7] corresponds to net_volume_period
        per_symbol_table_data.sort(key=lambda x: x[7], reverse=True)

        # Overall Summary Table
        total_period_buy_orders = sum(1 for t in processed_period_transactions if t['action'] == 'buy' or t['action'] == 'initial')
        total_period_sell_orders = sum(1 for t in processed_period_transactions if t['action'] == 'sell')
        grand_total_period_commission = sum(t['commission'] for t in processed_period_transactions)

        summary_data = [
            ["Period", f"Last {duration}" if duration else "All Time"],
            ["Total Txns", len(processed_period_transactions)],
            ["Buys", total_period_buy_orders],
            ["Sells", total_period_sell_orders],
            ["Total Comm.", f"${grand_total_period_commission:,.2f}"],
            ["Net P/L", f"${grand_total_net_pnl_period:,.2f}"]
        ]

        print("\n--- Overall Transactions Summary ---")
        print(tabulate(summary_data, tablefmt="grid", stralign="right"))

        if per_symbol_table_data:
            headers = [
                "Symbol", "Buy Vol", "Avg Buy $", "Buy Cost",
                "Sell Vol", "Avg Sell $", "Sell Income",
                "Net Vol", "Net P/L", "Last Trade"
            ]
            print("\n--- Per-Symbol Transaction Details (Period) ---")
            print(tabulate(per_symbol_table_data, headers=headers, tablefmt="grid", stralign="right"))
        else:
            print("\nNo per-symbol transaction data to display for the period (after considering initial positions).")

    def _parse_transaction_numerics(self, t_data: Dict[str, str]) -> Optional[tuple[int, float, float]]:
        """Helper to parse numeric fields from a transaction data dictionary."""
        try:
            size = int(t_data['size'])
            price = float(t_data['price'])
            commission = float(t_data['commission'])
            return size, price, commission
        except (ValueError, KeyError) as e:
            dbg_error(f"Skipping transaction due to data conversion/missing key error: {t_data} - {e}")
            return None

    # You might add other broker-specific methods here as needed,

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
            broker_type='mock',
            initial_cash=100000.0,
            commission_rate=0.007,
            state_filepath=example_state_file
        )
        print(f"BrokerManager initialized with {manager.broker_type} broker.")
        print(f"Initial Cash: ${manager.get_balance():,.2f}")
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
    print(f"Current Cash: ${manager.get_balance():,.2f}")
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
        broker_type='mock',
        initial_cash=5000.0, # Different initial cash, will be overwritten by loaded state
        commission_rate=0.001, # Different commission, will be overwritten by loaded state
        state_filepath=example_state_file # Must point to the same file to load
    )
    print(f"Manager 2 Initial Cash (before connect): ${manager2.get_balance():,.2f}")
    manager2.connect() # Connects and loads state from the file
    print("State loaded implicitly via connect.")

    # --- Verify Loaded State in New Manager ---
    print("\n--- Verifying Loaded State (Manager 2) ---")
    print(f"Manager 2 Loaded Cash: ${manager2.get_balance():,.2f}")
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
