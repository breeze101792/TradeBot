import traceback
import pandas as pd
import uuid
from datetime import datetime, timedelta # Import timedelta
from tabulate import tabulate
from typing import List, Dict, Any, Optional, Tuple # Added Tuple for _parse_transaction_numerics return

from utility.debug import *
from trading.tradedata import Database
from broker.brokermanager import BrokerManager

from broker.order.constant import OrderAction

# Trade instance for each trade with symbol(Product).
# A Trade object represents a full deal, which can contain multiple transactions.
class Trade:
    """
    Represents a full trade cycle, from opening to closing.
    A trade consists of one or more transactions.
    """
    def __init__(self, symbol: str, action: OrderAction, price: float, size: int, timestamp: int, commission: float = 0.0, strategy: str = ''):
        self.trade_id = str(uuid.uuid4())
        self.symbol = symbol
        self.strategy = strategy
        self.transactions = []
        self.add_transaction(action, price, size, timestamp, commission)

    def add_transaction(self, action: OrderAction, price: float, size: int, timestamp: int, commission: float = 0.0):
        """Adds a transaction to this trade."""
        transaction = {
            'action': action,
            'price': price,
            'size': size,
            'timestamp': timestamp,
            'commission': commission
        }
        self.transactions.append(transaction)

    @property
    def is_open(self) -> bool:
        """A trade is open if the total bought size is greater than the total sold size."""
        return self.current_size > 0

    @property
    def current_size(self) -> int:
        """Returns the current size held for this trade."""
        total_bought = sum(t['size'] for t in self.transactions if t['action'] == OrderAction.BUY)
        total_sold = sum(t['size'] for t in self.transactions if t['action'] == OrderAction.SELL)
        return total_bought - total_sold

    def calculate_profit(self) -> float:
        """Calculates the realized profit for a closed trade."""
        if self.is_open:
            return 0.0  # Profit is only realized when the trade is closed

        total_revenue = sum(t['price'] * t['size'] for t in self.transactions if t['action'] == OrderAction.SELL)
        total_cost = sum(t['price'] * t['size'] for t in self.transactions if t['action'] == OrderAction.BUY)
        total_commission = sum(t['commission'] for t in self.transactions)

        return total_revenue - total_cost - total_commission

    def __repr__(self):
        return f"Trade(trade_id={self.trade_id}, symbol={self.symbol}, size={self.current_size}, is_open={self.is_open})"

# record trading with Trade.
class Recorder:
    """
    Records all trades into database.
    """
    def __init__(self, data_path: str = ''):
        """
        Initializes the Recorder. The record_file_path is ignored and kept for compatibility.
        """
        if data_path != '':
            self.db = Database(data_path)
        else:
            broker_path = './'
            if BrokerManager.broker_path is not None:
                broker_path = BrokerManager.broker_path
            self.db = Database(os.path.join(broker_path, 'trade.db'))

        self.db.connect()
        self.db.setup()
    def __finalize__(self):
        self.db.close()

    def get_open_trades(self, symbol: str = None) -> list['Trade']:
        """
        Retrieves all open trades, optionally filtered by symbol.
        An open trade is one where the sum of bought sizes is greater than the sum of sold sizes.
        """
        open_trades_info = self.db.get_open_trades_info(symbol)
        if not open_trades_info:
            return []

        open_trade_ids = [row[0] for row in open_trades_info]
        open_trades_map = {row[0]: {'symbol': row[1], 'strategy': row[2]} for row in open_trades_info}

        transactions_list = self.db.get_transactions_for_trades(open_trade_ids)
        transactions_df = pd.DataFrame(
            transactions_list,
            columns=['trade_id', 'action', 'price', 'size', 'timestamp', 'commission']
        )

        reconstructed_trades = []
        for trade_id, trade_info in open_trades_map.items():
            trade_transactions = transactions_df[transactions_df['trade_id'] == trade_id]
            if trade_transactions.empty:
                continue

            first_trans = trade_transactions.iloc[0]
            trade = Trade(
                symbol=trade_info['symbol'],
                action=OrderAction[first_trans['action']],
                price=first_trans['price'],
                size=int(first_trans['size']),
                timestamp=first_trans['timestamp'],
                commission=first_trans['commission'],
                strategy=trade_info['strategy']
            )
            trade.trade_id = trade_id

            for _, trans_row in trade_transactions.iloc[1:].iterrows():
                trade.add_transaction(
                    action=OrderAction[trans_row['action']],
                    price=trans_row['price'],
                    size=int(trans_row['size']),
                    timestamp=trans_row['timestamp'],
                    commission=trans_row['commission']
                )
            
            reconstructed_trades.append(trade)
            
        return reconstructed_trades

    def get_records(self, symbol: str) -> list['Trade']:
        """
        Retrieves all open trades for a given symbol.
        
        Args:
            symbol: The symbol to retrieve trades for.
            
        Returns:
            A list of open Trade objects for the specified symbol.
        """
        return self.get_open_trades(symbol)

    def add_record(self, symbol: str, action: OrderAction, price: float, size: int, timestamp: int, commission: float = 0.0, strategy: str = ''):
        """Adds a new transaction record. It will either be added to an existing open trade
        for the same symbol or a new trade will be created."""
        open_trades = self.get_open_trades(symbol)
        open_trade = open_trades[0] if open_trades else None

        if open_trade:
            if strategy and open_trade.strategy != strategy:
                dbg_warning(f"Strategy changed for open trade {open_trade.trade_id}. "
                            f"Original: '{open_trade.strategy}', New: '{strategy}'. "
                            f"The original strategy will be kept.")
            
            self.db.insert_transaction(open_trade.trade_id, action, price, size, timestamp, commission)
            open_trade.add_transaction(action, price, size, timestamp, commission) # update in-memory object for logging
            if not open_trade.is_open:
                dbg_info(f"Closed trade for {symbol}. Trade ID: {open_trade.trade_id}")
        else:
            if action == OrderAction.BUY:
                new_trade = Trade(symbol, action, price, size, timestamp, commission, strategy)
                self.db.insert_trade(new_trade.trade_id, new_trade.symbol, new_trade.strategy)
                self.db.insert_transaction(new_trade.trade_id, action, price, size, timestamp, commission)
                dbg_info(f"Opened new trade for {symbol}. Trade ID: {new_trade.trade_id}")
            else:
                # This could be a short sale, but for now we'll assume it's an error if no open long position exists.
                dbg_warning(f"Received a SELL for {symbol} but no open trade found. Ignoring.")
                return

        self.show_records(symbol=symbol)
    
    def get_report(self, period: Optional[str] = 'month') -> pd.DataFrame:
        """
        Generates a profit/loss report for closed trades, grouped by the specified period.
        Args:
            period: The period to group the report by ('day', 'week', 'month', 'year'). Defaults to 'month'.
        Returns:
            A pandas DataFrame with the report.
        """
        closed_trades_info = self.db.get_closed_trades_info()
        if not closed_trades_info:
            dbg_info("No closed trades to report.")
            return pd.DataFrame()

        closed_trade_ids = [row[0] for row in closed_trades_info]
        closed_trades_map = {row[0]: {'symbol': row[1], 'strategy': row[2]} for row in closed_trades_info}

        transactions_list = self.db.get_transactions_for_trades(closed_trade_ids)
        transactions_df = pd.DataFrame(
            transactions_list,
            columns=['trade_id', 'action', 'price', 'size', 'timestamp', 'commission']
        )

        reconstructed_trades = []
        for trade_id, trade_info in closed_trades_map.items():
            trade_transactions = transactions_df[transactions_df['trade_id'] == trade_id]
            if trade_transactions.empty:
                continue

            # Find the first transaction to initialize the Trade object
            # This assumes transactions are ordered by timestamp, which they are from get_transactions_for_trades
            first_trans = trade_transactions.iloc[0]
            trade = Trade(
                symbol=trade_info['symbol'],
                action=OrderAction[first_trans['action']],
                price=first_trans['price'],
                size=int(first_trans['size']),
                timestamp=first_trans['timestamp'],
                commission=first_trans['commission'],
                strategy=trade_info['strategy']
            )
            trade.trade_id = trade_id

            # Add subsequent transactions
            for _, trans_row in trade_transactions.iloc[1:].iterrows():
                trade.add_transaction(
                    action=OrderAction[trans_row['action']],
                    price=trans_row['price'],
                    size=int(trans_row['size']),
                    timestamp=trans_row['timestamp'],
                    commission=trans_row['commission']
                )
            reconstructed_trades.append(trade)

        report_data = []
        for trade in reconstructed_trades:
            if not trade.is_open: # Only include closed trades in the report
                report_data.append({
                    'trade_id': trade.trade_id,
                    'symbol': trade.symbol,
                    'strategy': trade.strategy,
                    'profit': trade.calculate_profit(),
                    'close_timestamp': max(t['timestamp'] for t in trade.transactions) # Use the latest transaction timestamp as close time
                })
        
        if not report_data:
            dbg_info("No closed trades with calculated profit to report.")
            return pd.DataFrame()

        report_df = pd.DataFrame(report_data)
        report_df['close_datetime'] = pd.to_datetime(report_df['close_timestamp'], unit='ms')

        # Grouping by period
        if period == 'day':
            report_df['period'] = report_df['close_datetime'].dt.to_period('D')
        elif period == 'week':
            report_df['period'] = report_df['close_datetime'].dt.to_period('W')
        elif period == 'month':
            report_df['period'] = report_df['close_datetime'].dt.to_period('M')
        elif period == 'year':
            report_df['period'] = report_df['close_datetime'].dt.to_period('Y')
        else:
            dbg_warning(f"Invalid period specified: {period}. Defaulting to 'month'.")
            report_df['period'] = report_df['close_datetime'].dt.to_period('M')

        grouped_report = report_df.groupby('period').agg(
            total_profit=('profit', 'sum'),
            num_trades=('trade_id', 'count'),
            avg_profit_per_trade=('profit', 'mean')
        ).reset_index()

        grouped_report['period'] = grouped_report['period'].astype(str) # Convert Period objects to string for display
        return grouped_report

    def show_report(self, period: Optional[str] = 'month'):
        """
        Displays the profit/loss report in a tabular format.
        Args:
            period: The period to group the report by ('day', 'week', 'month', 'year'). Defaults to 'month'.
        """
        report_df = self.get_report(period)

        if report_df.empty:
            print(f"No closed trade report available for period: {period}.")
            return

        print(f"\n--- Profit/Loss Report by {period.capitalize()} ---")
        headers = ["Period", "Total Profit", "Number of Trades", "Avg Profit/Trade"]
        table_data = report_df[['period', 'total_profit', 'num_trades', 'avg_profit_per_trade']].values.tolist()
        
        # Format numerical columns
        for row in table_data:
            row[1] = f"{row[1]:.2f}" # Total Profit
            row[3] = f"{row[3]:.2f}" # Avg Profit/Trade

        print(tabulate(table_data, headers=headers, tablefmt="grid"))

    def show_records(self, symbol: str = None, strategy: str = None, duration: Optional[str] = None):
        """Displays the recorded trades and transactions in a tabular format.
        If a symbol is provided, only shows records for that symbol.
        If a strategy is provided, only shows records for that strategy.
        If a duration is provided ('day', 'week', 'month', 'year'), it shows open trades
        and trades with transactions within that duration."""
        
        # Get all open trades first, as they should always be shown
        open_trades_info = self.db.get_open_trades_info(symbol)
        open_trade_ids = {row[0] for row in open_trades_info} # Use a set for efficient lookup

        # Determine the time range for duration-based filtering
        filtered_trade_ids_by_duration = set()
        if duration:
            end_timestamp = int(datetime.now().timestamp() * 1000) # Current time in milliseconds
            start_timestamp = 0 # Default to beginning of time if duration not matched

            if duration == 'day':
                start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                start_timestamp = int(start_of_day.timestamp() * 1000)
            elif duration == 'week':
                start_of_week = datetime.now() - timedelta(days=datetime.now().weekday()) # Monday
                start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
                start_timestamp = int(start_of_week.timestamp() * 1000)
            elif duration == 'month':
                start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                start_timestamp = int(start_of_month.timestamp() * 1000)
            elif duration == 'year':
                start_of_year = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                start_timestamp = int(start_of_year.timestamp() * 1000)
            else:
                dbg_warning(f"Invalid duration specified: {duration}. Showing all trades.")
                duration = None # Reset duration to show all if invalid

            if duration:
                filtered_trade_ids_by_duration = set(self.db.get_trade_ids_by_transaction_time_range(start_timestamp, end_timestamp))

        # Combine trade IDs: all open trades + trades with recent transactions (if duration specified)
        all_relevant_trade_ids = open_trade_ids.union(filtered_trade_ids_by_duration)

        if not all_relevant_trade_ids:
            print("No trade records to show.")
            return

        # Fetch trade info for the combined set of IDs
        # This requires a new method in Database or filtering the existing get_trades_info result
        # For simplicity, let's fetch all trades and then filter in Python
        all_trades_info = self.db.get_trades_info(symbol, strategy)
        trades_df = pd.DataFrame(all_trades_info, columns=['trade_id', 'symbol', 'strategy'])
        
        # Filter trades_df to only include relevant trade_ids
        trades_df = trades_df[trades_df['trade_id'].isin(all_relevant_trade_ids)]

        if trades_df.empty:
            print("No trade records to show after filtering.")
            return

        trade_ids_to_fetch_transactions = trades_df['trade_id'].tolist()
        transactions_list = self.db.get_transactions_for_trades(trade_ids_to_fetch_transactions)
        transactions_df = pd.DataFrame(transactions_list, columns=['trade_id', 'action', 'price', 'size', 'timestamp', 'commission'])

        # Reconstruct trades to calculate is_open and current_size
        all_trades = []
        for _, trade_row in trades_df.iterrows():
            trade_id = trade_row['trade_id']
            trade_transactions = transactions_df[transactions_df['trade_id'] == trade_id]
            if trade_transactions.empty:
                continue

            first_trans = trade_transactions.iloc[0]
            trade = Trade(
                symbol=trade_row['symbol'],
                action=OrderAction[first_trans['action']],
                price=first_trans['price'],
                size=int(first_trans['size']),
                timestamp=first_trans['timestamp'],
                commission=first_trans['commission'],
                strategy=trade_row['strategy']
            )
            trade.trade_id = trade_id

            for _, trans_row in trade_transactions.iloc[1:].iterrows():
                trade.add_transaction(
                    action=OrderAction[trans_row['action']],
                    price=trans_row['price'],
                    size=trans_row['size'],
                    timestamp=trans_row['timestamp'],
                    commission=trans_row['commission']
                )
            all_trades.append(trade)

        if not all_trades:
            if symbol:
                print(f"No trade records found for symbol: {symbol}")
            else:
                print("No trade records to show.")
            return

        print("\n--- Trades Summary ---")
        headers = ["Trade ID", "Symbol", "Strategy", "Is Open", "Current Qty", "Transactions", "Trade Profit"]
        table_data = []
        for t in all_trades:
            table_data.append([t.trade_id, t.symbol, t.strategy, t.is_open, t.current_size, len(t.transactions), f"{t.calculate_profit():.2f}"])
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

        print("\n--- Transactions ---")
        transaction_headers = ["Trade ID", "Symbol", "Strategy", "Action", "Price", "Size", "Datetime", "Commission"]
        transaction_data = []
        # Sort trades by the timestamp of their first transaction for chronological order
        for trade in sorted(all_trades, key=lambda x: x.transactions[0]['timestamp']):
            for t in trade.transactions:
                transaction_data.append([
                    trade.trade_id,
                    trade.symbol,
                    trade.strategy,
                    t['action'].name,
                    t['price'],
                    t['size'],
                    datetime.fromtimestamp(t['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                    t['commission']
                ])
        print(tabulate(transaction_data, headers=transaction_headers, tablefmt="grid"))


