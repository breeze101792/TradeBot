import backtrader as bt
from backtrader.brokers import BackBroker

class AnalysisBroker(BackBroker):
    def __init__(self, **kwargs):
        """
        Initialize the broker with a Shioaji-compatible API instance.

        Args:
            shioaji_api: An instance of real Shioaji or FakeShioajiAPI.

        Raises:
            ValueError: If no API is provided.
            TypeError: If required methods are missing.
        """
        super().__init__(**kwargs)
