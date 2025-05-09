import backtrader as bt
from strategy.basic.basicstrategy import BasicStrategy
# Assuming basicstrategy might contain helper functions or base classes, keep the import.
# If basicstrategy is not used, it could be removed.
# from strategy.basicstrategy import * # Commented out if not used, uncomment if needed.

class BollingerRebound(BasicStrategy):
    """
    A strategy that buys when the price touches or crosses below the lower
    Bollinger Band and sells when the price crosses back above the middle band.
    Uses print() for logging.
    """
    NAME="BR"
    params = (
        ('period', 20),     # Period for the moving average
        ('devfactor', 2.0), # Standard deviation factor for the bands
    )

    def __init__(self):
        """Initializes the strategy."""
        # Keep track of Bollinger Bands and entry price per data feed
        self.bb_dict = {}
        self.entry_price = {}

        # print(f"Strategy Name: {self.NAME}")
        # print(f"Parameters: Period={self.p.period}, DevFactor={self.p.devfactor}")

        for i, d in enumerate(self.datas):
            data_name = d._name or f'Data{i}' # Use provided name or generate one
            self.bb_dict[data_name] = bt.indicators.BollingerBands(
                d.close,
                period=self.p.period,
                devfactor=self.p.devfactor
            )
            self.entry_price[data_name] = None
            # print(f"Initialized Bollinger Bands for {data_name}")

    # Removed notify_order as we are simplifying and using print in next()

    def next(self):
        """Executes the strategy logic on each bar."""
        current_date = self.datas[0].datetime.date(0) # Get current date for printing

        for i, d in enumerate(self.datas):
            name = d._name or f'Data{i}' # Use consistent naming
            bb = self.bb_dict[name]
            pos = self.getposition(d).size
            close = d.close[0]
            lower = bb.lines.bot[0]
            mid = bb.lines.mid[0]
            upper = bb.lines.top[0] # Get upper band too, for context

            # Print current status for this data feed
            dbg_trace(f'{current_date.isoformat()} {name} - Pos: {pos}, Close: {close:.2f}, Lower: {lower:.2f}, Mid: {mid:.2f}, Upper: {upper:.2f}')

            # Entry Condition: No position and close below lower band
            if pos == 0 and close < lower:
                dbg_log(f'{current_date.isoformat()} {name} - ENTRY SIGNAL: Close {close:.2f} < Lower Band {lower:.2f}. Placing BUY order.')
                self.buy(data=d)
                # Record entry price immediately (simplification)
                # Note: This won't be the exact execution price, but the close price triggering the signal.
                # For more accuracy, notify_order would be needed.
                self.entry_price[name] = close

            # Exit Condition: Position exists and close above middle band
            # elif pos > 0 and close > mid:
            elif pos > 0 and close > upper:
                dbg_log(f'{current_date.isoformat()} {name} - EXIT SIGNAL: Close {close:.2f} > Mid Band {mid:.2f}. Placing SELL order.')
                self.sell(data=d)
                # Reset entry price immediately (simplification)
                self.entry_price[name] = None
            # else:
                # Optional: Print when no action is taken
                # print(f'{current_date.isoformat()} {name} - No signal. Holding position or waiting.')

