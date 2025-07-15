import os
import csv
from datetime import datetime, timedelta
from collections import defaultdict
from tabulate import tabulate
from typing import List, Dict, Any, Optional
import threading
import traceback

from utility.debug import dbg_info, dbg_error, dbg_warning, dbg_debug
from broker.order.constant import OrderAction, OrderPrice
from broker.brokers.base.basebroker import BaseBroker

class TransactionManager:
    def __init__(self, broker: BaseBroker, lock: threading.Lock, transaction_log_path: str):
        self.broker = broker
        self._lock = lock
        self.transaction_log_path = transaction_log_path
        os.makedirs(os.path.dirname(self.transaction_log_path), exist_ok=True)
        self._log_transaction_init()

    def _log_transaction_init(self):
        """
        Initializes the transaction log file if it does not exist.
        If the file is new, it writes the CSV header and logs any existing positions
        as 'initial' state entries.
        """
        log_exists = os.path.exists(self.transaction_log_path)
        now_iso = datetime.now().isoformat()

        # TODO, We didn't handle the transacion when the file arleady exist, but not done by this program.
        if not log_exists:
            # File doesn't exist, create it, log initial positions, then log the current transaction
            # only use it for init
            # FIXME, use lock to lock it up.
            self._lock.acquire()
            try:
                initial_positions = self.broker.get_all_positions()
                cash_balance = self.broker.get_balance()
            except Exception as e:
                dbg_error(e)
            
                traceback_output = traceback.format_exc()
                dbg_error(traceback_output)
            finally:
                self._lock.release()
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

    def log_transaction(self, symbol: str, action: str, size: int, price: float, 
                        commission: float, cash_balance: float):
        """
        Logs a transaction to the CSV file. Ensures the log file is initialized first.
        
        Args:
            symbol (str): Trading symbol.
            action (str): 'BUY' or 'SELL' (or 'initial' for initial position logging).
            size (int): Number of shares.
            price (float): Execution price per share.
            commission (float): Commission paid for the transaction.
            cash_balance (float): Cash balance after the transaction.
        """
        # log_exists = os.path.exists(BrokerManager.transaction_log_path)
        now_iso = datetime.now().isoformat()

        # File exists, append the current transaction
        with open(self.transaction_log_path, 'a', newline='') as f:
            writer = csv.writer(f)
            current_transaction_row = [
                now_iso,
                symbol,
                action,
                int(size),
                price,
                commission,
                cash_balance
            ]
            writer.writerow(current_transaction_row)

    def get_transactions(self) -> List[Dict[str, Any]]:
        """
        Reads and returns all logged transactions from the CSV file.

        Returns:
            List[Dict[str, Any]]: A list of transaction records, where each record is a dictionary
                                  with keys matching the CSV headers (e.g., 'timestamp', 'symbol', 'action').
                                  Returns an empty list if the transaction log file does not exist.
        """
        if not os.path.exists(self.transaction_log_path):
            return []
            
        with open(self.transaction_log_path, 'r') as f:
            reader = csv.DictReader(f)
            return list(reader)

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
        transactions = self.get_transactions()
        current_positions = self.broker.get_all_positions()

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
                        current_price = self.broker.get_last_price(symbol, OrderPrice.LAST)
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
            if duration == 'day':
                cutoff = now - timedelta(days=1)
            elif duration == 'month':
                cutoff = now - timedelta(days=30)
            elif duration == 'year':
                cutoff = now - timedelta(days=365)
            elif duration == 'week':
                cutoff = now - timedelta(days=7)
            else:
                raise ValueError("Invalid duration. Use 'day', 'month', 'year' or 'week'")
            
            filtered_transactions = [t for t in transactions 
                                     if datetime.fromisoformat(t['timestamp']) >= cutoff]

        if not filtered_transactions: # No transactions at all, or no transactions for the specified duration
            if duration:
                print(f"No transactions found for the specified period ('{duration}').")
            else:
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
                # TODO, remove initial after check no one use it.
                # buy/BUY/sell/SELL is for compatiable.
                if action in [OrderAction.BUY.value, 'initial']:
                    cost_of_this_buy = (price * size) + commission
                    current_pos_state['total_cost_basis'] += cost_of_this_buy
                    current_pos_state['size'] += size
                elif action in [OrderAction.SELL.value]:
                    if current_pos_state['size'] > 0:
                        avg_cost_per_share = current_pos_state['total_cost_basis'] / current_pos_state['size']
                        cost_basis_of_sold_shares = avg_cost_per_share * min(size, current_pos_state['size'])
                        current_pos_state['total_cost_basis'] -= cost_basis_of_sold_shares
                    current_pos_state['size'] -= size
                    current_pos_state['size'] = max(0, current_pos_state['size'])
                    if current_pos_state['size'] == 0:
                        current_pos_state['total_cost_basis'] = 0.0
                else:
                    dbg_warning(f"Unkown action: {action}")
        
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

            if action == OrderAction.BUY.value or action == 'initial': # 'initial' should ideally not be in period transactions
                details['period_buy_volume'] += size
                details['period_buy_value'] += price * size
                details['period_buy_commissions'] += commission
                
                cost_of_this_buy = (price * size) + commission
                current_pnl_state['current_total_cost_basis'] += cost_of_this_buy
                current_pnl_state['current_size'] += size
            
            elif action == OrderAction.SELL.value:
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
            
            if data['period_buy_volume'] == 0 and data['period_sell_volume'] == 0:
                continue
            
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
        total_period_buy_orders = sum(1 for t in processed_period_transactions if t['action'] == OrderAction.BUY.value or t['action'] == 'initial')
        total_period_sell_orders = sum(1 for t in processed_period_transactions if t['action'] == OrderAction.SELL.value)
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
        """
        Helper method to safely parse numeric fields (size, price, commission)
        from a raw transaction data dictionary read from CSV.

        Args:
            t_data (Dict[str, str]): A dictionary representing a single transaction record,
                                     where values are typically strings.

        Returns:
            Optional[tuple[int, float, float]]: A tuple containing (size, price, commission)
                                                as their respective numeric types if parsing is successful.
                                                Returns None if any conversion fails or a key is missing.
        """
        try:
            # Not sure we need to support float, but just keep for compatiable.
            if '.' in t_data['size']:
                size = float(t_data['size'])
            else:
                size = int(t_data['size'])
            price = float(t_data['price'])
            commission = float(t_data['commission'])
            return size, price, commission
        except (ValueError, KeyError) as e:
            dbg_error(f"Skipping transaction due to data conversion/missing key error: {t_data} - {e}")
            return None

