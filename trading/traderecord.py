import traceback
import pandas as pd
import os
import uuid
from datetime import datetime
from tabulate import tabulate

from utility.debug import *
from core.config import AppConfigManager

from broker.order.constant import OrderAction
from broker.brokermanager import BrokerManager

# Trade instance for each trade with symbol(Product).
# A Trade object represents a full deal, which can contain multiple transactions.
class Trade:
    """
    Represents a full trade cycle, from opening to closing.
    A trade consists of one or more transactions.
    """
    def __init__(self, symbol: str, action: OrderAction, price: float, size: float, timestamp: int, commission: float = 0.0, strategy: str = ''):
        self.trade_id = str(uuid.uuid4())
        self.symbol = symbol
        self.strategy = strategy
        self.transactions = []
        self.add_transaction(action, price, size, timestamp, commission)

    def add_transaction(self, action: OrderAction, price: float, size: float, timestamp: int, commission: float = 0.0):
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
    def current_size(self) -> float:
        """Returns the current size held for this trade."""
        total_bought = sum(t['size'] for t in self.transactions if t['action'] == OrderAction.BUY)
        total_sold = sum(t['size'] for t in self.transactions if t['action'] == OrderAction.SELL)
        return total_bought - total_sold

    def __repr__(self):
        return f"Trade(trade_id={self.trade_id}, symbol={self.symbol}, size={self.current_size}, is_open={self.is_open})"

# record trading with Trade.
class Recorder:
    """
    Records all trades and saves them to a file.
    """
    trades = []
    _loaded = False

    def __init__(self, record_file_path: str = ''):
        if not record_file_path:
            recorder_file_name = 'trading_record.csv'
            if BrokerManager.broker_path is None:
                dbg_error(f"Broker path is None, please do broker manager init befreo using it. Store on current folder.")
                self.record_file = os.path.join('./', recorder_file_name)
            else:
                self.record_file = os.path.join(BrokerManager.broker_path, recorder_file_name)
        else:
            self.record_file = record_file_path
        
        if not Recorder._loaded:
            self.load_records()
            Recorder._loaded = True

    def get_records(self, symbol: str) -> list['Trade']:
        """
        Retrieves all open trades for a given symbol.
        
        Args:
            symbol: The symbol to retrieve trades for.
            
        Returns:
            A list of open Trade objects for the specified symbol.
        """
        return [t for t in Recorder.trades if t.symbol == symbol and t.is_open]
    def add_record(self, symbol: str, action: OrderAction, price: float, size: float, timestamp: int, commission: float = 0.0, strategy: str = ''):
        """Adds a new transaction record. It will either be added to an existing open trade
        for the same symbol or a new trade will be created."""
        open_trade = next((t for t in Recorder.trades if t.symbol == symbol and t.is_open), None)

        if open_trade:
            open_trade.add_transaction(action, price, size, timestamp, commission)
            if not open_trade.is_open:
                dbg_info(f"Closed trade for {symbol}. Trade ID: {open_trade.trade_id}")
        else:
            if action == OrderAction.BUY:
                new_trade = Trade(symbol, action, price, size, timestamp, commission, strategy)
                Recorder.trades.append(new_trade)
                dbg_info(f"Opened new trade for {symbol}. Trade ID: {new_trade.trade_id}")
            else:
                # This could be a short sale, but for now we'll assume it's an error if no open long position exists.
                dbg_warning(f"Received a SELL for {symbol} but no open trade found. Ignoring.")
                return

        self.show_records(symbol=symbol)
        self.save_records()

    def save_records(self):
        """Saves all transactions from all trades to a CSV file."""
        if not Recorder.trades:
            return

        try:
            all_transactions = []
            for trade in Recorder.trades:
                for transaction in trade.transactions:
                    record = transaction.copy()
                    record['trade_id'] = trade.trade_id
                    record['symbol'] = trade.symbol
                    record['strategy'] = trade.strategy
                    record['action'] = record['action'].name
                    record['datetime'] = datetime.fromtimestamp(record['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    all_transactions.append(record)

            if not all_transactions:
                return

            df = pd.DataFrame(all_transactions)
            # Reorder columns for clarity
            cols = ['trade_id', 'symbol', 'strategy', 'action', 'price', 'size', 'timestamp', 'datetime', 'commission']
            df = df[[c for c in cols if c in df.columns]]

            record_dir = os.path.dirname(self.record_file)
            if record_dir and not os.path.exists(record_dir):
                os.makedirs(record_dir)

            df.to_csv(self.record_file, index=False)
            dbg_info('Trade records saved to ' + self.record_file)
        except Exception as e:
            dbg_error(f"Error saving trade records to {self.record_file}: {e}")
            dbg_error(traceback.format_exc())


    def load_records(self):
        """Loads trade records from a CSV file and reconstructs trades."""
        if not os.path.exists(self.record_file):
            dbg_warning(f"Record file not found: {self.record_file}")
            return

        try:
            df = pd.read_csv(self.record_file)
            if df.empty:
                dbg_info(f"Record file is empty: {self.record_file}")
                return

            # Replace NaN values for optional fields
            df.fillna({'commission': 0.0, 'strategy': ''}, inplace=True)

            # Group transactions by trade_id to reconstruct trades
            trades_map = {}
            # Sort by timestamp to process transactions in order
            df.sort_values(by='timestamp', inplace=True)

            for _, row in df.iterrows():
                if pd.isna(row.get('trade_id')) or pd.isna(row['symbol']) or pd.isna(row['action']) or pd.isna(row['price']) or pd.isna(row['size']) or pd.isna(row['timestamp']):
                    dbg_warning(f"Skipping row with missing essential data: {row.to_dict()}")
                    continue

                trade_id = row['trade_id']
                if trade_id not in trades_map:
                    # Create a new Trade object for the first transaction of a deal
                    trade = Trade(
                        symbol=row['symbol'],
                        action=OrderAction[row['action']],
                        price=float(row['price']),
                        size=float(row['size']),
                        timestamp=int(row['timestamp']),
                        commission=float(row['commission']),
                        strategy=row['strategy']
                    )
                    trade.trade_id = trade_id # Preserve original trade_id
                    trades_map[trade_id] = trade
                else:
                    # Add subsequent transactions to the existing trade
                    trades_map[trade_id].add_transaction(
                        action=OrderAction[row['action']],
                        price=float(row['price']),
                        size=float(row['size']),
                        timestamp=int(row['timestamp']),
                        
                        commission=float(row['commission'])
                    )

            Recorder.trades = list(trades_map.values())
            dbg_info(f"Loaded {len(Recorder.trades)} trades from {self.record_file}")
        except Exception as e:
            dbg_error(f"Error loading trade records from {self.record_file}: {e}")
            dbg_error(traceback.format_exc())
    def show_records(self, symbol: str = None):
        """Displays the recorded trades and transactions in a tabular format.
        If a symbol is provided, only shows records for that symbol."""
        if not Recorder.trades:
            print("No trade records to show.")
            return

        trades_to_show = Recorder.trades
        if symbol:
            trades_to_show = [t for t in Recorder.trades if t.symbol == symbol]

        if not trades_to_show:
            if symbol:
                print(f"No trade records found for symbol: {symbol}")
            else:
                print("No trade records to show.")
            return

        print("\n--- Trades Summary ---")
        headers = ["Trade ID", "Symbol", "Strategy", "Is Open", "Current Qty", "Transactions"]
        table_data = []
        for t in trades_to_show:
            table_data.append([t.trade_id, t.symbol, t.strategy, t.is_open, t.current_size, len(t.transactions)])
        print(tabulate(table_data, headers=headers, tablefmt="grid"))

        print("\n--- Transactions ---")
        transaction_headers = ["Trade ID", "Symbol", "Strategy", "Action", "Price", "size", "Datetime", "commission"]
        transaction_data = []
        # Sort trades by the timestamp of their first transaction for chronological order
        for trade in sorted(trades_to_show, key=lambda x: x.transactions[0]['timestamp']):
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


