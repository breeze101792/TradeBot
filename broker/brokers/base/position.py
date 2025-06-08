import json
import os
import datetime as dt
from datetime import date, time # Import date for tracking open date
from utility.debug import *
from broker.order.constant import OrderStatus, OrderAction

class Position:
    """Represents a holding in a specific asset."""
    def __init__(self, symbol: str, size: int = 0, average_entry_price: float = 0.0, initial_entry_price: float = 0.0, open_date: datetime.date = None):
        self.symbol = symbol
        self.size = size
        self.average_entry_price = average_entry_price
        # Store the price of the very first buy transaction for this position instance
        self.initial_entry_price = initial_entry_price
        # Store the date when the position was first opened
        self.open_date = open_date

    def update(self, action: OrderAction, size: int, price: float):
        """Updates the position based on a transaction."""
        total_cost_before = self.size * self.average_entry_price
        if action == OrderAction.BUY:
            # Record the price and date of the first buy
            if self.initial_entry_price == 0.0: # Assuming initial price is 0 only before first buy
                self.initial_entry_price = price
            if self.open_date is None: # Record open date only once
                self.open_date = date.today()

            new_total_cost = total_cost_before + (size * price)
            self.size += size
            if self.size != 0:
                self.average_entry_price = new_total_cost / self.size
            else:
                # Should not happen if buying, but handle defensively
                self.average_entry_price = 0.0
        elif action == OrderAction.SELL:
            # Average entry price doesn't change on sell, PnL is realized
            self.size -= size
            if self.size < 0:
                dbg_warning(f"Position size for {self.symbol} went negative ({self.size}). Resetting to 0.")
                # This indicates an oversell, handle as per strategy logic (e.g., raise error or cap at 0)
                self.size = 0
            if self.size == 0:
                self.average_entry_price = 0.0 # Reset average price when position is closed
                self.initial_entry_price = 0.0 # Also reset initial entry price when closed
                self.open_date = None # Reset open date when closed
        else:
            dbg_error(f"Unknown Action: {action} for symbol {self.symbol}")

    def get_market_value(self, current_price: float) -> float:
        """Calculates the current market value of the position."""
        return self.size * current_price

    def __repr__(self):
        open_date_str = self.open_date.isoformat() if self.open_date else 'N/A'
        return f"Position(symbol='{self.symbol}', size={self.size}, avg_entry={self.average_entry_price:.2f}, initial_entry={self.initial_entry_price:.2f}, open_date='{open_date_str}')"

    def to_dict(self) -> dict:
        """Converts the Position object to a dictionary."""
        return {
            'symbol': self.symbol,
            'size': self.size,
            'average_entry_price': self.average_entry_price,
            'initial_entry_price': self.initial_entry_price,
            # Convert date to ISO string for JSON compatibility, handle None
            'open_date': self.open_date.isoformat() if self.open_date else None
        }
