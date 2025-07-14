
import uuid

# Local file
from utility.udb import *
from utility.debug import *

class Database(uDatabase):
    # def __init__(self):
    #     pass
    def setup_tables(self):
        dbg_info("Initiialize Tablse")

        # Stock ID
        #####################################################

        # Trades table
        query_str = '''
                    CREATE TABLE IF NOT EXISTS Trades (
                        trade_id TEXT PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        strategy TEXT
                    );
                    '''
        self.execute(query_str)

        # Transactions table
        query_str = '''
                    CREATE TABLE IF NOT EXISTS Transactions (
                        transaction_id TEXT PRIMARY KEY,
                        trade_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        price REAL NOT NULL,
                        size INTEGER NOT NULL,
                        timestamp INTEGER NOT NULL,
                        commission REAL,
                        FOREIGN KEY(trade_id) REFERENCES Trades(trade_id)
                    );
                    '''
        self.execute(query_str)

        self.commit()

        return True

    def insert_trade(self, trade_id, symbol, strategy):
        query = f"INSERT INTO Trades (trade_id, symbol, strategy) VALUES ('{trade_id}', '{symbol}', '{strategy}')"
        self.execute(query)
        self.commit()

    def insert_transaction(self, trade_id, action, price, size, timestamp, commission):
        transaction_id = str(uuid.uuid4())
        query = f"""
            INSERT INTO Transactions (transaction_id, trade_id, action, price, size, timestamp, commission)
            VALUES ('{transaction_id}', '{trade_id}', '{action.name}', {price}, {size}, {timestamp}, {commission})
        """
        self.execute(query)
        self.commit()

    def get_open_trades_info(self, symbol: str = None) -> list:
        """
        Retrieves information about open trades, optionally filtered by symbol.
        """
        where_clause = f"WHERE T.symbol = '{symbol}'" if symbol else ""
        
        query = f"""
            SELECT T.trade_id, T.symbol, T.strategy
            FROM Trades T
            JOIN Transactions T2 ON T.trade_id = T2.trade_id
            {where_clause}
            GROUP BY T.trade_id
            HAVING SUM(CASE WHEN T2.action = 'BUY' THEN T2.size ELSE -T2.size END) > 0
        """
        return self.execute(query)

    def get_transactions_for_trades(self, trade_ids: list[str]) -> list:
        """
        Retrieves all transactions for a given list of trade IDs.
        """
        if not trade_ids:
            return []
        trade_ids_str = ", ".join([f"'{tid}'" for tid in trade_ids])
        query = f"SELECT trade_id, action, price, size, timestamp, commission FROM Transactions WHERE trade_id IN ({trade_ids_str}) ORDER BY timestamp ASC"
        return self.execute(query)

    def get_trades_info(self, symbol: str = None) -> list:
        """
        Retrieves trade information, optionally filtered by symbol.
        """
        where_clause = f"WHERE symbol = '{symbol}'" if symbol else ""
        trades_query = f"SELECT trade_id, symbol, strategy FROM Trades {where_clause}"
        return self.execute(trades_query)

