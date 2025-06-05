from enum import Enum # Import Enum
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Any, Dict

class Event(Enum):
    OrderFilled = "OrderFilled" # Indicates that an order has been successfully executed and filled.
    OrderFailed = "OrderFailed" # Signifies that an order could not be filled due to various reasons (e.g., insufficient funds, market conditions).
    OrderPending = "OrderPending" # Represents an order that has been placed but not yet filled or canceled.
    OrderCanceled = "OrderCanceled" # Denotes an order that was previously placed but has now been canceled.

def default_event_callback(event: Event, data = None):
    dbg_info(f"Event: {event}")

@dataclass
class OrderEvent:
    """
    Represents a specific event related to an order's lifecycle.
    This class encapsulates the event type and all relevant data associated with the order.
    """
    event_type: Event
    timestamp: datetime
    symbol: str
    action: str # 'buy' or 'sell'
    size: int
    price: float # Execution price for filled, requested price for others
    commission: float # Commission paid for filled orders, 0 for others
    status: str # A string representation of the order's status (e.g., 'filled', 'failed', 'pending', 'canceled')
    order_id: Optional[str] = None # Unique identifier for the order
    reason: Optional[str] = None # Reason for failure or cancellation

    def __post_init__(self):
        # Ensure timestamp is always a datetime object
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the OrderEvent object to a dictionary for logging or serialization."""
        return {
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'action': self.action,
            'size': self.size,
            'price': self.price,
            'commission': self.commission,
            'status': self.status,
            'order_id': self.order_id,
            'reason': self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Creates an OrderEvent object from a dictionary."""
        return cls(
            event_type=Event(data['event_type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            symbol=data['symbol'],
            action=data['action'],
            size=data['size'],
            price=float(data['price']),
            commission=float(data['commission']),
            status=data['status'],
            order_id=data.get('order_id'),
            reason=data.get('reason')
        )

    def show_event(self, title: str = "Order Event Details"):
        """
        Displays the current OrderEvent object in a formatted table using tabulate.
        """
        from tabulate import tabulate # Import tabulate locally to avoid circular dependency if not already imported

        headers = [
            "Timestamp", "Event Type", "Symbol", "Action", "Size",
            "Price", "Commission", "Status", "Order ID", "Reason"
        ]
        
        row = [
            self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            self.event_type.value,
            self.symbol,
            self.action,
            self.size,
            f"{self.price:,.2f}",
            f"{self.commission:,.2f}",
            self.status,
            self.order_id if self.order_id else 'N/A',
            self.reason if self.reason else 'N/A'
        ]
        table_data = [row] # Wrap the single row in a list for tabulate

        print(f"\n--- {title} ---")
        print(tabulate(table_data, headers=headers, tablefmt="grid", stralign="right"))
