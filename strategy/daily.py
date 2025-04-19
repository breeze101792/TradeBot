import backtrader as bt
import pandas as pd
from utility.debug import *
from strategy.basicstrategy import *

# Daily test MACE Strategy
# this is for experiment on daily evaluation.
class DailyStrategy(BasicStrategy):
    NAME="DAILY"
    trading_date = None
    last_trade = {
    "date"          : None,
    "code"          : "",
    "action"        : "none", # sell/buy/None
    "current_price" : 0,
    "target_price"  : 0,      # sell when price falls to this (target for short position)
    "stop_price"    : 0       # stop-loss for short; if price rises above this, close position
    }
    params = (
        ("short_period", 5),  # Short period for moving average (5 days)
        ("long_period", 20),  # Long period for moving average (20 days)
        ("risk_per_trade", 0.2),  # Max risk per trade (20%)
        ("trailing_stop_pct", 0.05),  # Trailing stop percentage (5%)
        ("trailing_takeprofit_pct", 0.10),  # Trailing take profit percentage (10%)
    )

    def __init__(self):
        self.sma_short = {data: bt.indicators.SimpleMovingAverage(data, period=self.params.short_period) for data in self.datas}
        self.sma_long = {data: bt.indicators.SimpleMovingAverage(data, period=self.params.long_period) for data in self.datas}
        self.stop_loss = {}  # Record stop loss prices
        self.take_profit = {}  # Record take profit prices
        self.trailing_stop = {}  # Trailing stop loss prices
        self.trailing_takeprofit = {}  # Trailing take profit prices

    def __is_trading_date(self, data_date):
        if self.trading_date is None:
            return True
        if data_date ==  self.trading_date:
            # Your trading logic here
            # print("Running strategy logic on", self.datas[0].datetime.date(0))
            return True
        else:
            return False
    def reset_status(self):
        self.trading_date = None
        self.last_trade = {
        "date"          : None,
        "code"          : "",
        "action"        : "none", # sell/buy/None
        "current_price" : 0,
        "target_price"  : 0,      # sell when price falls to this (target for short position)
        "stop_price"    : 0       # stop-loss for short; if price rises above this, close position
        }

    def update_trading_info(self, date, code, action,current_price , target_price, stop_price):
        self.last_trade['date']          = date
        self.last_trade['code']          = code
        self.last_trade['action']        = action
        self.last_trade['current_price'] = current_price
        self.last_trade['target_price']  = target_price
        self.last_trade['stop_price']    = stop_price

        # if action == 'buy':
        #     trade_info = self.last_trade
        #     dbg_info(f"Update Trade info {trade_info['code']}@{trade_info['date']}: Action: {trade_info['action']}, Current: {trade_info['current_price']:.2f}, Target: {trade_info['target_price']:.2f}, Stop: {trade_info['stop_price']:.2f}")

    def next(self):
        if not self.__is_trading_date(self.datas[0].datetime.date(0)):
            return
        # normal we add only one data at a time, so the len will be 1.
        for data in self.datas:
            pos = self.getposition(data)
            price = data.close[0]

            # Entry: Short MA crosses above Long MA
            if not pos and self.sma_short[data][0] > self.sma_long[data][0] and self.sma_short[data][-1] <= self.sma_long[data][-1]:
                size = self.broker.get_cash() * self.params.risk_per_trade / price
                self.buy(data=data, size=size)
                self.stop_loss[data] = price * 0.95  # Set initial stop loss (5% down)
                self.take_profit[data] = price * 1.2  # Set initial take profit (20% up)
                self.trailing_stop[data] = price * 0.95  # Set initial trailing stop loss (5% down)
                self.trailing_takeprofit[data] = price * 1.2  # Set initial trailing take profit (20% up)
                dbg_log(f"📈 [{self.data.datetime.date(0)}]{data._name} Bought @ {price:.2f}, Stop Loss: {self.stop_loss[data]:.2f}, Take Profit: {self.take_profit[data]:.2f}")
                # Update last trade info after buying
                self.update_trading_info(
                    date=self.data.datetime.date(0),
                    code=data._name,
                    action="buy",
                    current_price=price,
                    target_price=self.take_profit[data], # Using take_profit as target for long
                    stop_price=self.stop_loss[data]
                )

            # Exit: Short MA crosses below Long MA or hit stop loss/take profit
            elif pos:
                # Update trailing stop and take profit when the price moves in your favor
                if price > self.trailing_takeprofit[data]:
                    self.trailing_takeprofit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Adjust trailing take profit
                if price > self.trailing_stop[data]:
                    self.trailing_stop[data] = max(self.trailing_stop[data], price * (1 - self.params.trailing_stop_pct))  # Adjust trailing stop loss

                # Exit conditions
                if price < self.trailing_stop[data]:
                    self.sell(data=data, size=pos.size)
                    dbg_log(f"📉 [{self.data.datetime.date(0)}]{data._name} Trailing Stop Loss hit @ {price:.2f}")
                    # Update last trade info after selling (trailing stop)
                    self.update_trading_info(
                        date=self.data.datetime.date(0),
                        code=data._name,
                        action="sell",
                        current_price=price,
                        target_price=0, # No target after closing
                        stop_price=0    # No stop after closing
                    )

                elif price > self.trailing_takeprofit[data]:
                    self.sell(data=data, size=pos.size)
                    dbg_log(f"🏆 [{self.data.datetime.date(0)}]{data._name} Trailing Take Profit hit @ {price:.2f}")
                    # Update last trade info after selling (trailing take profit)
                    self.update_trading_info(
                        date=self.data.datetime.date(0),
                        code=data._name,
                        action="sell",
                        current_price=price,
                        target_price=0, # No target after closing
                        stop_price=0    # No stop after closing
                    )

                elif self.sma_short[data][0] < self.sma_long[data][0] or price < self.stop_loss[data]:
                    self.sell(data=data, size=pos.size)
                    dbg_log(f"📉 [{self.data.datetime.date(0)}]{data._name} Exit Signal (SMA Cross/Stop Loss) @ {price:.2f}") # Improved log message
                    # Update last trade info after selling (SMA cross or initial stop)
                    self.update_trading_info(
                        date=self.data.datetime.date(0),
                        code=data._name,
                        action="sell",
                        current_price=price,
                        target_price=0, # No target after closing
                        stop_price=0    # No stop after closing
                    )
            else:
                # No position held
                dbg_log(f"- [{self.data.datetime.date(0)}]{data._name} No Position @ {price:.2f}")

                # Update last trade info when no position is held
                self.update_trading_info(
                    date=self.data.datetime.date(0),
                    code=data._name,
                    action="none",
                    current_price=price,
                    target_price=0, # No target
                    stop_price=0    # No stop
                )
