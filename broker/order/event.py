from enum import Enum # Import Enum
from dataclasses import dataclass
from datetime import datetime

class Event(Enum):
    OrderFilled = "OrderFilled" # Indicates that an order has been successfully executed and filled.
    OrderFailed = "OrderFailed" # Signifies that an order could not be filled due to various reasons (e.g., insufficient funds, market conditions).
    OrderPending = "OrderPending" # Represents an order that has been placed but not yet filled or canceled.
    OrderCanceled = "OrderCanceled" # Denotes an order that was previously placed but has now been canceled.

def default_event_callback(event: Event, data = None):
    print(f"Event: {event}")
