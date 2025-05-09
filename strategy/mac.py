import backtrader as bt
import pandas as pd
from math import ceil
from utility.debug import *
from strategy.basicstrategy import *

# Moving Average Crossover
# this is for experiment on daily evaluation.
class MovingAverageCrossoverStrategy(BasicStrategy):
    NAME="MovingAverageCrossover"
    params = (
        ("short_period", 10),  # Short period for moving average (5 days)
        ("long_period", 50),  # Long period for moving average (20 days)
        # ("risk_per_trade", 0.2),  # Max risk per trade (20%), this will affect the efficent of using cash.
        ("risk_per_trade", 0.8),  # Max risk per trade (20%)
        ("trailing_stop_pct", 0.05),  # Trailing stop percentage (5%)
        ("trailing_takeprofit_pct", 0.05),  # Trailing take profit percentage (10%)
    )

    def __init__(self):
        super().__init__()
        # Indicator
        self.sma_short = {data: bt.indicators.SimpleMovingAverage(data, period=self.params.short_period) for data in self.datas}
        self.sma_long = {data: bt.indicators.SimpleMovingAverage(data, period=self.params.long_period) for data in self.datas}

        # risk control
        self.stop_loss = {}  # Record stop loss prices
        self.take_profit = {}  # Record take profit prices
        self.trailing_stop = {}  # Trailing stop loss prices
        self.trailing_takeprofit = {}  # Trailing take profit prices

    def next(self):
        if not self.is_trading_date(self.datas[0].datetime.date(0)):
            return
        # normal we add only one data at a time, so the len will be 1.
        for data in self.datas:
            pos = self.getposition(data)
            price = data.close[0]
            # dbg_info(f"[{self.data.datetime.date(0)}]{data._name} Price:{price:.2f}, pos:{pos.size}")

            # Exit: Short MA crosses below Long MA or hit stop loss/take profit
            if pos.size > 0:
                # Update trailing stop and take profit when the price moves in your favor
                if price > self.trailing_stop[data]:
                    self.trailing_stop[data] = max(self.trailing_stop[data], price * (1 - self.params.trailing_stop_pct))  # Adjust trailing stop loss

                # Exit conditions
                if price < self.stop_loss[data]:
                    # entry stop loss.
                    self.sell(data=data, size=pos.size)
                    dbg_log(f"📉 [{self.data.datetime.date(0)}]{data._name} Exit Signal (SMA Cross/Stop Loss) @ {price:.2f}, pos:{pos.size}") # Improved log message
                elif price < self.trailing_stop[data]:
                    # trailing stop loss.

                    # calc size to sell
                    lot_size = pos.size / self.LOT_UNIT
                    sell_pos = 0
                    if lot_size >= 2:
                        sell_pos = ceil(lot_size/2) * self.LOT_UNIT
                    else:
                        sell_pos = lot_size * self.LOT_UNIT
                    # dbg_info(f'Selling debug: {pos.size}->{sell_pos}')
                    self.sell(data=data, size=sell_pos)

                    # Update to next stop lossing point.
                    self.trailing_stop[data] = max(self.trailing_stop[data], price * (1 - self.params.trailing_stop_pct))  # Adjust trailing stop loss

                    dbg_log(f"📉 [{self.data.datetime.date(0)}]{data._name} Trailing Stop Loss hit @ {price:.2f}, pos:{sell_pos}")

                # we don't sell it when it's going higher.
                elif price > self.trailing_takeprofit[data]:
                    # adjust moving profit.

                    # we don't sell out all stock at once.
                    lot_size = pos.size / self.LOT_UNIT
                    sell_pos = 0
                    if lot_size >= 2:
                        sell_pos = ceil(lot_size/2) * self.LOT_UNIT
                    else:
                        sell_pos = lot_size * self.LOT_UNIT
                    # dbg_info(f'Selling debug: {pos.size}->{sell_pos}')
                    self.sell(data=data, size=sell_pos)

                    # adjust next profit sell.
                    if price > self.trailing_takeprofit[data]:
                        self.trailing_takeprofit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Adjust trailing take profit

                    # update trailing stop
                    self.trailing_stop[data] = price * (1 - self.params.trailing_stop_pct)  # Set initial trailing stop loss (5% down)

                    dbg_log(f"🏆 [{self.data.datetime.date(0)}]{data._name} Trailing Take Profit hit @ {price:.2f}")

                elif self.sma_short[data][0] < self.sma_long[data][0]:
                    # strategy safty.
                    self.sell(data=data, size=pos.size)
                    dbg_log(f"📉 [{self.data.datetime.date(0)}]{data._name} Exit Signal (SMA Cross/Stop Loss) @ {price:.2f}, pos:{pos.size}") # Improved log message
            # Entry: Short MA crosses above Long MA
            elif not pos and self.sma_short[data][0] > self.sma_long[data][0] and self.sma_short[data][-1] <= self.sma_long[data][-1]:
                lot_size = int(self.broker.get_cash() * self.params.risk_per_trade / (price * self.LOT_UNIT))
                size = lot_size * self.LOT_UNIT
                self.buy(data=data, size=size)

                # update init paramaters.
                self.stop_loss[data] = price * (1 - self.params.trailing_stop_pct)  # Set initial stop loss (5% down)
                self.take_profit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Set initial take profit (20% up)

                self.trailing_stop[data] = price * (1 - self.params.trailing_stop_pct)  # Set initial trailing stop loss (5% down)
                self.trailing_takeprofit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Set initial trailing take profit (20% up)

                dbg_log(f"📈 [{self.data.datetime.date(0)}]{data._name} Bought @ {price:.2f}, pos:{pos.size}, Stop Loss: {self.stop_loss[data]:.2f}, Take Profit: {self.take_profit[data]:.2f}")

            else:
                # No position held
                # dbg_log(f"- [{self.data.datetime.date(0)}]{data._name} No Position @ {price:.2f}")
                pass
