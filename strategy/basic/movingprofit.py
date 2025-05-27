import backtrader as bt
import pandas as pd
from math import ceil
from utility.debug import *
from strategy.basic.basicstrategy import BasicExitStrategy

class MovingProfitStrategy(BasicExitStrategy):
    NAME="MovingProfit"
    params = (
        # ("risk_per_trade", 0.8),  # Max risk per trade (20%)
        # ("trailing_stop_pct", 0.05),  # Trailing stop percentage (5%)
        # ("trailing_takeprofit_pct", 0.05),  # Trailing take profit percentage (5%)
        ("risk_per_trade", 0.8),  # Max risk per trade (20%)
        ("trailing_stop_pct", 0.06),  # Trailing stop percentage (5%)
        ("trailing_takeprofit_pct", 0.16),  # Trailing take profit percentage (15%)
    )

    def __init__(self):
        super().__init__()
        # Indicator

        # risk control
        self.stop_loss = {}  # Record stop loss prices
        self.take_profit = {}  # Record take profit prices
        self.trailing_stop = {}  # Trailing stop loss prices
        self.trailing_takeprofit = {}  # Trailing take profit prices

        # stra initial
        self.stra_initial()

    def next(self):
        # dbg_info(f"[{self.datas[0].datetime.date(0)}] {self.is_trading_date(self.datas[0].datetime.date(0))}")
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
                    # self.sell(data=data, size=pos.size)
                    self.close()
                    dbg_trace(f"📉 [{self.data.datetime.date(0)}]{data._name} Exit Signal (Stop Loss) @ {price:.2f}, pos:{pos.size}") # Improved log message
                elif self.stra_sell_out(data):
                    # strategy safty.
                    # self.sell(data=data, size=pos.size)
                    self.close()
                    dbg_trace(f"📉 [{self.data.datetime.date(0)}]{data._name} Exit Signal (Strategy Stop Loss) @ {price:.2f}, pos:{pos.size}") # Improved log message
                # elif price > self.take_profit[data]:
                #     # strategy safty.
                #     self.sell(data=data, size=pos.size)
                #     dbg_trace(f"🏆 [{self.data.datetime.date(0)}]{data._name} Take Profit hit @ {price:.2f}")
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
                    # self.trailing_stop[data] = max(self.trailing_stop[data], price * (1 - self.params.trailing_stop_pct))  # Adjust trailing stop loss

                    dbg_trace(f"📉 [{self.data.datetime.date(0)}]{data._name} Trailing Stop Loss hit @ {price:.2f}, pos:{sell_pos}")

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

                    # since we hit the take_profi, ensure the profit.
                    self.stop_loss[data] = max(self.stop_loss[data], price * (1 - self.params.trailing_stop_pct))  # Adjust trailing stop loss

                    # update trailing stop, devide 2 so we could make a difference between stop_loss and trailing_stop
                    self.trailing_stop[data] = price * (1 - self.params.trailing_stop_pct / 2)  # Set initial trailing stop loss (5% down)

                    dbg_trace(f"🏆 [{self.data.datetime.date(0)}]{data._name} Trailing Take Profit hit @ {price:.2f}")

            # Entry: Short MA crosses above Long MA
            elif not pos and self.stra_buy_in(data):
                lot_size = int(self.broker.get_cash() * self.params.risk_per_trade / (price * self.LOT_UNIT))
                size = lot_size * self.LOT_UNIT
                self.buy(data=data, size=size)

                # update init paramaters.
                self.stop_loss[data] = price * (1 - self.params.trailing_stop_pct)  # Set initial stop loss (5% down)
                self.take_profit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Set initial take profit (20% up)

                self.trailing_stop[data] = price * (1 - self.params.trailing_stop_pct)  # Set initial trailing stop loss (5% down)
                self.trailing_takeprofit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Set initial trailing take profit (20% up)

                dbg_trace(f"📈 [{self.data.datetime.date(0)}]{data._name} Bought @ {price:.2f}, pos:{pos.size}, Stop Loss: {self.stop_loss[data]:.2f}, Take Profit: {self.take_profit[data]:.2f}")

            else:
                # No position held
                # dbg_trace(f"- [{self.data.datetime.date(0)}]{data._name} No Position @ {price:.2f}")
                pass
