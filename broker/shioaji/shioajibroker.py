import backtrader as bt
from backtrader.brokers import BackBroker

class FakeShioajiAPI:
    """
    A fake Shioaji-like API to simulate basic trading actions.
    This mimics the interface needed by the custom broker.
    """
    def __init__(self):
        self.cash = 1000000
        self.positions = {}

    def place_order(self, symbol, action, price, size):
        """
        Simulate placing an order and immediately mark as filled.

        Args:
            symbol (str): The stock symbol.
            action (str): 'buy' or 'sell'.
            price (float): The order price.
            size (int): The order quantity.

        Returns:
            dict: Fake order execution result.
        """
        return {
            'symbol': symbol,
            'action': action,
            'price': price,
            'size': size,
            'status': 'filled'
        }

    def get_balance(self):
        return self.cash

    def get_position(self, symbol):
        return self.positions.get(symbol, 0)

    def get_price(self, symbol):
        return 100  # Fixed fake market price

class ShioajiBroker(BackBroker):
    """
    A Backtrader-compatible broker that wraps around a Shioaji-compatible API.
    Works with either a real Shioaji instance or a FakeShioajiAPI for testing.
    Inherits from BackBroker to integrate with Backtrader's internal order handling.
    """
    def __init__(self, shioaji_api=None, **kwargs):
        """
        Initialize the broker with a Shioaji-compatible API instance.

        Args:
            shioaji_api: An instance of real Shioaji or FakeShioajiAPI.

        Raises:
            ValueError: If no API is provided.
            TypeError: If required methods are missing.
        """
        super().__init__(**kwargs)
        if not shioaji_api:
            # raise ValueError("shioaji_api must be provided (either real or fake implementation)")
            print("shioaji_api must be provided (either real or fake implementation)")
            shioaji_api = FakeShioajiAPI()

        required_methods = ['get_balance', 'get_position', 'get_price', 'place_order']
        for method in required_methods:
            if not hasattr(shioaji_api, method):
                raise TypeError(f"Provided shioaji_api is missing required method: {method}")

        self.shioaji = shioaji_api

    def getcash(self):
        """
        Get available cash from the API.

        Returns:
            float: Available cash.
        """
        return self.shioaji.get_balance()

    def getvalue(self):
        """
        Get total portfolio value (cash + current position value).

        Returns:
            float: Total portfolio value.
        """
        value = self.shioaji.get_balance()
        for symbol, pos in self.shioaji.positions.items():
            try:
                price = self.shioaji.get_price(symbol)
                value += pos * price
            except Exception as e:
                print(f"[ShioajiBacktraderBroker] Error getting price for {symbol}: {e}")
        return value

    def getposition(self, data):
        """
        Return the current position for a data feed (stock).

        Args:
            data: The Backtrader data feed.

        Returns:
            int: Position size.
        """
        symbol = data._name
        return self.shioaji.get_position(symbol)

    def _execute_order(self, order):
        """
        Intercept and execute an order through the external API.

        Args:
            order (bt.Order): A Backtrader order instance.
        """
        symbol = order.data._name
        size = order.size
        price = order.created.price if order.created.price else self.shioaji.get_price(symbol)
        action = 'buy' if order.isbuy() else 'sell'

        try:
            result = self.shioaji.place_order(symbol, action, price, size)
            order.executed.price = price
            order.executed.size = size
            order.executed.value = price * size
            order.status = order.Completed

            # Update simulated positions and cash
            if action == 'buy':
                self.shioaji.cash -= price * size
                self.shioaji.positions[symbol] = self.shioaji.positions.get(symbol, 0) + size
            else:
                self.shioaji.cash += price * size
                self.shioaji.positions[symbol] = self.shioaji.positions.get(symbol, 0) - size

            self._orderspending.remove(order)
            self._orderscompleted.append(order)
            self.notify(order)

            print(f"[ShioajiBacktraderBroker] Executed {action.upper()} {symbol} {size} @ {price}")

        except Exception as e:
            order.status = order.Rejected
            self._orderspending.remove(order)
            self.notify(order)
            print(f"[ShioajiBacktraderBroker] Order execution failed: {e}")

