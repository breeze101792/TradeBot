from typing import Any, Optional, Dict # Import Any, Optional, Dict
from datetime import datetime
from dataclasses import dataclass, field # Import field
from tabulate import tabulate # Import tabulate locally

from utility.debug import * # Replace standard logging with custom debug system

@dataclass
class OrderTracker:
    """
    Represents a specific event related to an order's lifecycle.
    This class encapsulates the event type and all relevant data associated with the order.
    """
    timestamp: datetime
    symbol: str
    action: str # 'buy' or 'sell'
    size: int
    price: float # Execution price for filled, requested price for others
    status: str # A string representation of the order's status (e.g., 'filled', 'failed', 'pending', 'canceled')
    reason: Optional[str] = None # Reason for failure or cancellation
    commission: Optional[float] = None # Commission incurred for the order
    
    # This field holds the original order instance (e.g., MockOrder) if needed, but not for init/repr
    order_instance: Any = field(init=False, repr=False, default=None)

    # def __init__(self, order_instance):
    #     self.order_instance = order_instance
    def __post_init__(self):
        # Ensure timestamp is always a datetime object if it somehow comes as string (e.g., from_dict)
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the OrderTracker object to a dictionary for logging or serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'action': self.action,
            'size': self.size,
            'price': self.price,
            'commission': self.commission,
            'status': self.status,
            'reason': self.reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Creates an OrderTracker object from a dictionary."""
        # This will use the dataclass's generated __init__
        print('from_dict', data['timestamp'])
        instance = cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            symbol=data['symbol'],
            action=data['action'],
            size=data['size'],
            price=float(data['price']),
            commission=data.get('commission', 0),
            status=data['status'],
            reason=data.get('reason', None),
            order_instance=data.get('order_instance', None),
        )

    def show_order(self, title: str = "Order Tracker Details"):
        headers = [
            "Timestamp", "Symbol", "Action", "Size",
            "Price", "Commission", "Status", "Reason"
        ]
        table_data = [[
            self.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            self.symbol,
            self.action,
            self.size,
            f"{self.price:,.2f}",
            f"{self.commission:,.2f}" if self.commission is not None else 'N/A',
            self.status,
            self.reason if self.reason else 'N/A'
        ]]

        dbg_info(f"\n--- {title} ---")
        print(tabulate(table_data, headers=headers, tablefmt="grid", stralign="right"))
