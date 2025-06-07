
from datetime import date, time, datetime # Import date and datetime for tracking open date and order events
from enum import Enum # Import Enum
from dataclasses import dataclass, field # Import field
from typing import Any, Optional, Dict # Import Any, Optional, Dict

from broker.event import Event
@dataclass
class MockOrder:
    """
    This class is for mocking as private data class of mockbroker to save order info.
    """
    event_type: Event
    timestamp: datetime
    symbol: str
    action: str # 'buy' or 'sell'
    size: int
    price: float # Execution price for filled, requested price for others
    commission: float # Commission paid for filled orders, 0 for others
    status: str # A string representation of the order's status (e.g., 'filled', 'failed', 'pending', 'canceled')
    reason: Optional[str] = None # Reason for failure or cancellation

    def __post_init__(self):
        # Ensure timestamp is always a datetime object
        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the MockOrder object to a dictionary for logging or serialization."""
        return {
            'event_type': self.event_type.value,
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
        """Creates an MockOrder object from a dictionary."""
        return cls(
            event_type=Event(data['event_type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            symbol=data['symbol'],
            action=data['action'],
            size=data['size'],
            price=float(data['price']),
            commission=float(data['commission']),
            status=data['status'],
            reason=data.get('reason')
        )
