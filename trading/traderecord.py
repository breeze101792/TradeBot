import traceback
import pandas as pd
import uuid
from datetime import datetime
from tabulate import tabulate

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
    
    def show_records(self, symbol: str = None, strategy: str = None):
        """Displays the recorded trades and transactions in a tabular format.
        If a symbol is provided, only shows records for that symbol.
        If a strategy is provided, only shows records for that strategy."""
        
        trades_info = self.db.get_trades_info(symbol, strategy)

        if not trades_info:
            print("No trade records to show.")
            return

        trades_df = pd.DataFrame(trades_info, columns=['trade_id', 'symbol', 'strategy'])
        trade_ids = [row['trade_id'] for index, row in trades_df.iterrows()]

        if not trade_ids:
            if symbol:
                print(f"No trade records found for symbol: {symbol}")
            else:
                print("No trade records to show.")
            return

        transactions_list = self.db.get_transactions_for_trades(trade_ids)
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


