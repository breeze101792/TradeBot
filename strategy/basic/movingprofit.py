import backtrader as bt
import pandas as pd
from math import ceil, floor

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
        # ("trailing_takeprofit_pct", 0.16),  # Trailing take profit percentage (15%)
        ("trailing_takeprofit_pct", 0.08),  # Trailing take profit percentage (15%)
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

        # liquidity check
        # TODO, under dev
        self.liquidity_check = True
        if self.liquidity_check is True:
            # dbg_info(f'Enable liquidity check. For exp, we shows this message.')
            # Volume
            self.LIQUIDITY_VOL_THRESHOLD = 50 * 1000
            self.sma_vol = bt.indicators.SimpleMovingAverage(self.data.volume, period=20)
            # Turn over, maybe add it latter.
            # self.LIQUIDITY_TOV_THRESHOLD = 50 * 10 * 1000 # 1M
            # self.sma_tov = bt.indicators.SimpleMovingAverage(self.data.turnover, period=20)
        if self.p.trailing_takeprofit_pct <= self.p.trailing_stop_pct:
            dbg_error(f'trailing_takeprofit_pct({self.p.trailing_takeprofit_pct}) should bigger then trailing_stop_pct({self.p.trailing_stop_pct}).')
            raise

    def calc_selling_size(self, current_size, current_price):
        # def_parts = 2
        def_parts = 5
        sell_pos = 0

        try:
            lot_size = current_size / self.LOT_UNIT
            if lot_size >= def_parts and floor(lot_size/def_parts) * self.LOT_UNIT * current_price >= self.MIN_CASH_PER_TRADE:
                sell_pos = int(ceil(lot_size/def_parts) * self.LOT_UNIT)
            else:
                sell_pos = lot_size * self.LOT_UNIT
        except Exception as e:
            dbg_error(f"Error calculating sell_pos: {e}")
            sell_pos = 0 # Default to 0 if an error occurs
        return sell_pos
    def next(self):
        if not self.is_trading_date(self.datas[0].datetime.date(0)):
            return
        # dbg_error(f"Daily: [{self.datas[0].datetime.date(0)}] {self.is_trading_date(self.datas[0].datetime.date(0))}")
        # normal we add only one data at a time, so the len will be 1.
        for data in self.datas:
            pos = self.getposition(data)
            price = data.close[0]

            # Debug info
            log_message = f"Next: [{self.data.datetime.date(0)}]{data._name} @ {price:.2f}, pos:{pos.size}"
            if data in self.stop_loss:
                log_message += f", Stop Loss: {self.stop_loss[data]:.2f}"
            if data in self.take_profit:
                log_message += f", Take Profit: {self.take_profit[data]:.2f}"
            if data in self.trailing_stop:
                log_message += f", Trailing Stop: {self.trailing_stop[data]:.2f}"
            if data in self.trailing_takeprofit:
                log_message += f", Trailing Take Profit: {self.trailing_takeprofit[data]:.2f}"
            dbg_trace(log_message)
            # dbg_info(log_message)

            # Exit: Short MA crosses below Long MA or hit stop loss/take profit
            if pos.size > 0:
                # Update trailing stop and take profit when the price moves in your favor
                if price > self.trailing_stop[data] and self.trailing_stop[data] != self.stop_loss[data]:
                    ori_trailing_stop = self.trailing_stop[data]
                    self.trailing_stop[data] = max(self.trailing_stop[data], price * (1 - self.params.trailing_stop_pct))  # Adjust trailing stop loss
                    dbg_trace(f"[{self.data.datetime.date(0)}]{data._name} Update trailing stop from {ori_trailing_stop:.2f} to {self.trailing_stop[data]:.2f}")

                # Exit conditions
                if price < self.stop_loss[data]:
                    # entry stop loss.
                    self.sell(data=data, size=pos.size)
                    # self.close()
                    dbg_trace(f"📉 [{self.data.datetime.date(0)}]{data._name} Exit Signal (Stop Loss) @ {price:.2f}, pos:{pos.size}") # Improved log message
                elif self.stra_sell_out(data):
                    # strategy safty.
                    self.sell(data=data, size=pos.size)
                    # self.close()
                    dbg_trace(f"📉 [{self.data.datetime.date(0)}]{data._name} Exit Signal (Strategy Stop Loss) @ {price:.2f}, pos:{pos.size}") # Improved log message
                # elif price > self.take_profit[data]:
                #     # strategy safty.
                #     self.sell(data=data, size=pos.size)
                #     dbg_trace(f"🏆 [{self.data.datetime.date(0)}]{data._name} Take Profit hit @ {price:.2f}")
                elif price < self.trailing_stop[data]:
                    # trailing stop loss.

                    # calc size to sell
                    # lot_size = pos.size / self.LOT_UNIT
                    # sell_pos = 0
                    # if lot_size >= 2 and floor(lot_size/2) * self.LOT_UNIT * price >= self.MIN_CASH_PER_TRADE:
                    #     sell_pos = int(ceil(lot_size/2) * self.LOT_UNIT)
                    # else:
                    #     sell_pos = lot_size * self.LOT_UNIT
                    sell_pos = self.calc_selling_size(pos.size, price)
                    # dbg_info(f'Selling debug: {pos.size}->{sell_pos}')
                    self.sell(data=data, size=sell_pos)

                    # Update to next stop lossing point.
                    # self.trailing_stop[data] = max(self.trailing_stop[data], price * (1 - self.params.trailing_stop_pct))  # Adjust trailing stop loss

                    dbg_trace(f"📉 [{self.data.datetime.date(0)}]{data._name} Trailing Stop Loss hit @ {price:.2f}, pos:{sell_pos}")

                # we don't sell it when it's going higher.
                elif price > self.trailing_takeprofit[data]:
                    # adjust moving profit.

                    # we don't sell out all stock at once.
                    # lot_size = pos.size / self.LOT_UNIT
                    # sell_pos = 0
                    # if lot_size >= 2 and floor(lot_size/2) * self.LOT_UNIT * price >= self.MIN_CASH_PER_TRADE:
                    #     sell_pos = int(ceil(lot_size/2) * self.LOT_UNIT)
                    # else:
                    #     sell_pos = lot_size * self.LOT_UNIT
                    sell_pos = self.calc_selling_size(pos.size, price)
                    # dbg_info(f'Selling debug: {pos.size}->{sell_pos}')
                    self.sell(data=data, size=sell_pos)

                    # adjust next profit sell.
                    if price > self.trailing_takeprofit[data]:
                        self.trailing_takeprofit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Adjust trailing take profit

                    # since we hit the take_profi, ensure the profit.
                    # ori_stop_loss = self.stop_loss[data]
                    # self.stop_loss[data] = max(self.stop_loss[data], price * (1 - self.params.trailing_stop_pct))  # Adjust trailing stop loss
                    # dbg_error(f"update stop lose from {ori_stop_loss} to {self.stop_loss[data]}")

                    # use last profit point as stop_loss point.
                    ori_stop_loss = self.stop_loss[data]
                    self.stop_loss[data] = max(self.stop_loss[data], price * (1 - self.p.trailing_takeprofit_pct))  # Adjust trailing stop loss
                    dbg_trace(f"[{self.data.datetime.date(0)}]{data._name} Update stop loss from {ori_stop_loss:.2f} to {self.stop_loss[data]:.2f}")

                    # update trailing stop, devide 2 so we could make a difference between stop_loss and trailing_stop
                    # self.trailing_stop[data] = price * (1 - self.params.trailing_stop_pct / 2)  # Set initial trailing stop loss (5% down)
                    self.trailing_stop[data] = max(self.trailing_stop[data], price * (1 - self.params.trailing_stop_pct))  # Adjust trailing stop loss

                    dbg_trace(f"🏆 [{self.data.datetime.date(0)}]{data._name} Trailing Take Profit hit @ {price:.2f}")

            # Entry: Short MA crosses above Long MA
            elif not pos and self.stra_buy_in(data):
                if self.liquidity_check is True:
                    if self.sma_vol[0] < self.LIQUIDITY_VOL_THRESHOLD:
                        dbg_trace(f'Small VOL({self.sma_vol[0]}/{self.LIQUIDITY_VOL_THRESHOLD}), skip buying.')
                        return
                    # elif self.sma_tov[0] < self.LIQUIDITY_TOV_THRESHOLD:
                    #     dbg_info(f'Small TurnOver({self.sma_tov[0]}/{self.LIQUIDITY_TOV_THRESHOLD}), skip buying.')
                    #     return

                lot_size = int(self.broker.get_cash() * self.params.risk_per_trade / (price * self.LOT_UNIT))
                size = lot_size * self.LOT_UNIT
                # TODO, add minimum cash transaction check.
                self.buy(data=data, size=size)

                # update init paramaters.
                self.stop_loss[data] = price * (1 - self.params.trailing_stop_pct)  # Set initial stop loss (5% down)
                self.take_profit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Set initial take profit (20% up)

                self.trailing_stop[data] = price * (1 - self.params.trailing_stop_pct)  # Set initial trailing stop loss (5% down)
                self.trailing_takeprofit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Set initial trailing take profit (20% up)

                dbg_trace(f"📈 [{self.data.datetime.date(0)}]{data._name} Bought @ {price:.2f}, pos:{pos.size}, Stop Loss: {self.stop_loss[data]:.2f}, Take Profit: {self.take_profit[data]:.2f}, Trailing Stop: {self.trailing_stop[data]:.2f}, Trailing Take Profit: {self.trailing_takeprofit[data]:.2f}")

            else:
                # No position held
                # dbg_trace(f"- [{self.data.datetime.date(0)}]{data._name} No Position @ {price:.2f}")
                pass
