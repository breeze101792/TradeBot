from enum import Enum # Import Enum

class OrderAction(Enum):
    """
    Represents the action to be taken for an order.
    """
    BUY = "BUY"  # To buy an instrument
    SELL = "SELL"  # To sell an instrument
    UNKNOWN = "UNKNOWN" # Unknown order action

class OrderStatus(Enum):
    """
    Represents the current status of an order.
    """
    FILLED = "FILLED"  # The order has been completely filled.
    PARTIALLY_FILLED = "PARTIALLY_FILLED"  # Part of the order has been filled.
    PENDING_SUBMIT = "PENDING_SUBMIT"  # The order is waiting to be submitted.
    PENDING_CANCEL = "PENDING_CANCEL"  # The order is waiting to be cancelled.
    PRE_SUBMITTED = "PRE_SUBMITTED"  # The order has been validated but not yet sent to the exchange.
    SUBMITTED = "SUBMITTED"  # The order has been sent to the exchange.
    CANCELLED = "CANCELLED"  # The order has been cancelled.
    EXPIRED = "EXPIRED"  # The order has expired.
    REJECTED = "REJECTED"  # The order has been rejected by the exchange or broker.
    INACTIVE = "INACTIVE"  # The order is currently inactive.
    UNKNOWN = "UNKNOWN"  # Unknown order status.

class OrderPrice(Enum):
    """
    Represents the type of price to be used when placing an order.
    This determines how the order's execution price is determined in the market.

    - For a SELL order, the BID price is typically relevant (e.g., selling at the highest available bid).
    - For a BUY order, the ASK price is typically relevant (e.g., buying at the lowest available ask).
    - For orders aiming for immediate execution at the current market rate, LAST or MARKET prices are used.
    """
    BID = 'BID'  # The highest price a buyer is currently willing to pay for an instrument. Often used for limit sell orders.
    ASK = 'ASK'  # The lowest price a seller is currently willing to accept for an instrument. Often used for limit buy orders.
    LAST = 'LAST'  # The price at which the most recent trade for the instrument occurred. Can be used as a reference for market orders or stop orders.
    # MARKET = 'MARKET'  # An order to be executed immediately at the best available current price in the market, prioritizing speed over a specific price.
