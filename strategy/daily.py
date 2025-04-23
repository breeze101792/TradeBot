import backtrader as bt
import pandas as pd
from utility.debug import *
from strategy.basicstrategy import *

# Daily test MACE Strategy
# this is for experiment on daily evaluation.
class DailyMACStrategy(BasicStrategy):
    NAME="DMACE"
    trading_date = None
    last_trade = {
    "date"          : None,
    "code"          : "",
    "action"        : "none", # sell/buy/None
    "current_price" : 0,
    "target_price"  : 0,      # sell when price falls to this (target for short position)
    "stop_price"    : 0       # stop-loss for short; if price rises above this, close position
    }

    # recorder
    # Stores details of active buy positions:
    # {data: {'entry_date': date, 'avg_entry_price': float, 'remaining_size': int, 'total_cost': float}}
    active_trades = {}
    # Stores details of completed trade portions:
    # [{'code': str, 'entry_date': date, 'exit_date': date, 'avg_entry_price': float, 'exit_price': float, 'size': int, 'pnl': float, 'is_win': bool}]
    trading_history = []

    params = (
        ("short_period", 5),  # Short period for moving average (5 days)
        ("long_period", 20),  # Long period for moving average (20 days)
        # ("risk_per_trade", 0.2),  # Max risk per trade (20%), this will affect the efficent of using cash.
        ("risk_per_trade", 0.2),  # Max risk per trade (20%)
        ("trailing_stop_pct", 0.05),  # Trailing stop percentage (5%)
        ("trailing_takeprofit_pct", 0.10),  # Trailing take profit percentage (10%)
    )

    def __init__(self):
        # Indicator
        self.sma_short = {data: bt.indicators.SimpleMovingAverage(data, period=self.params.short_period) for data in self.datas}
        self.sma_long = {data: bt.indicators.SimpleMovingAverage(data, period=self.params.long_period) for data in self.datas}

        # risk control
        self.stop_loss = {}  # Record stop loss prices
        self.take_profit = {}  # Record take profit prices
        self.trailing_stop = {}  # Trailing stop loss prices
        self.trailing_takeprofit = {}  # Trailing take profit prices

        # reset status
        self.reset_status(clean_all = False)

    def w_buy(self, data, size = 1):
        """Wrapper for buy order execution and logging."""
        # entry_date = self.data.datetime.date(0) # Use current strategy date for logging intent
        # code = data._name
        # entry_price = data.close[0] # Use current close for logging intent
        # dbg_trace(f"Initiating Buy: [{entry_date}] {code} @ {entry_price:.2f} x {size}")
        self.buy(data=data, size=size)
    def w_sell(self, data, size = 1):
        """Wrapper for sell order execution and logging."""
        # exit_date = self.data.datetime.date(0) # Use current strategy date for logging intent
        # code = data._name
        # exit_price = data.close[0] # Use current close for logging intent
        # dbg_trace(f"Initiating Sell: [{exit_date}] {code} @ {exit_price:.2f} x {size}")
        self.sell(data=data, size=size)

    def is_trading_date(self, data_date):
        if self.trading_date is None:
            return True
        if data_date ==  self.trading_date:
            # Your trading logic here
            # print("Running strategy logic on", self.datas[0].datetime.date(0))
            return True
        else:
            return False
    def reset_status(self, clean_all = False):
        if clean_all is True:
            self.trading_date = None
            self.last_trade = {
            "date"          : None,
            "code"          : "",
            "action"        : "none", # sell/buy/None
            "current_price" : 0,
            "target_price"  : 0,      # sell when price falls to this (target for short position)
            "stop_price"    : 0       # stop-loss for short; if price rises above this, close position
            }

        # this is for calc winning rate.
        self.active_trades = {}
        # Stores details of completed trade portions:
        # [{'code': str, 'entry_date': date, 'exit_date': date, 'avg_entry_price': float, 'exit_price': float, 'size': int, 'pnl': float, 'is_win': bool}]
        self.trading_history = []

    def update_trading_info(self, date, code, action, current_price, target_price = 0, stop_price = 0):
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
        if not self.is_trading_date(self.datas[0].datetime.date(0)):
            return
        # normal we add only one data at a time, so the len will be 1.
        for data in self.datas:
            pos = self.getposition(data)
            price = data.close[0]

            # Exit: Short MA crosses below Long MA or hit stop loss/take profit
            if pos.size > 0:
                # Update trailing stop and take profit when the price moves in your favor
                if price > self.trailing_stop[data]:
                    self.trailing_stop[data] = max(self.trailing_stop[data], price * (1 - self.params.trailing_stop_pct))  # Adjust trailing stop loss

                # Exit conditions
                if price < self.stop_loss[data]:
                    self.w_sell(data=data, size=pos.size)
                    dbg_log(f"📉 [{self.data.datetime.date(0)}]{data._name} Exit Signal (SMA Cross/Stop Loss) @ {price:.2f}, pos:{pos.size}") # Improved log message
                    # Update last trade info after selling (SMA cross or initial stop)
                    self.update_trading_info(
                        date=self.data.datetime.date(0),
                        code=data._name,
                        action="sell",
                        current_price=price,
                    )
                elif price < self.trailing_stop[data]:
                    sell_pos = 0
                    if pos.size > 2:
                        self.w_sell(data=data, size=int(pos.size/2))
                        sell_pos = int(pos.size/2)
                    else:
                        self.w_sell(data=data, size=pos.size)
                        sell_pos = pos.size
                    # self.w_sell(data=data, size=pos.size)

                    # Update to next stop lossing point.
                    self.trailing_stop[data] = max(self.trailing_stop[data], price * (1 - self.params.trailing_stop_pct))  # Adjust trailing stop loss

                    dbg_log(f"📉 [{self.data.datetime.date(0)}]{data._name} Trailing Stop Loss hit @ {price:.2f}, pos:{sell_pos}")
                    # Update last trade info after selling (trailing stop)
                    self.update_trading_info(
                        date=self.data.datetime.date(0),
                        code=data._name,
                        action="sell",
                        current_price=price,
                    )

                # we don't sell it when it's going higher.
                # elif price > self.trailing_takeprofit[data]:
                #     # we don't sell out all stock at once.
                #     if pos.size > 2:
                #         self.w_sell(data=data, size=int(pos.size/2))
                #
                #     # adjust next profit sell.
                #     if price > self.trailing_takeprofit[data]:
                #         self.trailing_takeprofit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Adjust trailing take profit
                #
                #     dbg_log(f"🏆 [{self.data.datetime.date(0)}]{data._name} Trailing Take Profit hit @ {price:.2f}")
                #     # Update last trade info after selling (trailing take profit)
                #     self.update_trading_info(
                #         date=self.data.datetime.date(0),
                #         code=data._name,
                #         action="sell",
                #         current_price=price,
                #     )

                elif self.sma_short[data][0] < self.sma_long[data][0]:
                    self.w_sell(data=data, size=pos.size)
                    dbg_log(f"📉 [{self.data.datetime.date(0)}]{data._name} Exit Signal (SMA Cross/Stop Loss) @ {price:.2f}, pos:{pos.size}") # Improved log message
                    # Update last trade info after selling (SMA cross or initial stop)
                    self.update_trading_info(
                        date=self.data.datetime.date(0),
                        code=data._name,
                        action="sell",
                        current_price=price,
                    )
            # Entry: Short MA crosses above Long MA
            elif not pos and self.sma_short[data][0] > self.sma_long[data][0] and self.sma_short[data][-1] <= self.sma_long[data][-1]:
                size = int(self.broker.get_cash() * self.params.risk_per_trade / price)
                self.w_buy(data=data, size=size)

                # update init paramaters.
                self.stop_loss[data] = price * (1 - self.params.trailing_stop_pct)  # Set initial stop loss (5% down)
                self.take_profit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Set initial take profit (20% up)

                self.trailing_stop[data] = price * (1 - self.params.trailing_stop_pct)  # Set initial trailing stop loss (5% down)
                self.trailing_takeprofit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Set initial trailing take profit (20% up)

                dbg_log(f"📈 [{self.data.datetime.date(0)}]{data._name} Bought @ {price:.2f}, pos:{pos.size}, Stop Loss: {self.stop_loss[data]:.2f}, Take Profit: {self.take_profit[data]:.2f}")

                # Update last trade info after buying
                self.update_trading_info(
                    date=self.data.datetime.date(0),
                    code=data._name,
                    action="buy",
                    current_price=price,
                    target_price=self.take_profit[data], # Using take_profit as target for long
                    stop_price=self.stop_loss[data]
                )

            else:
                # No position held
                # dbg_log(f"- [{self.data.datetime.date(0)}]{data._name} No Position @ {price:.2f}")

                # Update last trade info when no position is held
                self.update_trading_info(
                    date=self.data.datetime.date(0),
                    code=data._name,
                    action="none",
                    current_price=price,
                )
    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            exec_price = order.executed.price
            exec_size = order.executed.size
            exec_cost = order.executed.value # Cost includes commission if set in broker
            exec_comm = order.executed.comm
            exec_date = bt.num2date(order.executed.dt).date() # Get execution date
            data = order.data # The specific data feed for this order
            code = data._name

            if order.isbuy():
                dbg_trace(f'BUY EXECUTED: {code}, Price: {exec_price:.2f}, Size: {exec_size}, Cost: {exec_cost:.2f}, Comm: {exec_comm:.2f}, Date: {exec_date}')

                if data in self.active_trades:
                    # Add to existing position
                    pos = self.active_trades[data]
                    new_total_cost = pos['total_cost'] + exec_cost
                    new_total_size = pos['remaining_size'] + exec_size
                    pos['avg_entry_price'] = new_total_cost / new_total_size if new_total_size else 0
                    pos['remaining_size'] = new_total_size
                    pos['total_cost'] = new_total_cost
                    # Keep the original entry_date
                    dbg_trace(f"Updated Active Trade {code}: Avg Price: {pos['avg_entry_price']:.2f}, Remaining Size: {pos['remaining_size']}")
                else:
                    # New position
                    self.active_trades[data] = {
                        'entry_date': exec_date,
                        'avg_entry_price': exec_price, # Initial avg price is the execution price
                        'remaining_size': exec_size,
                        'total_cost': exec_cost
                    }
                    dbg_trace(f"Opened Active Trade {code}: Entry Price: {exec_price:.2f}, Size: {exec_size}")

            elif order.issell():
                # when sell, exec_size shows negative number
                exec_size = -exec_size
                dbg_trace(f'SELL EXECUTED: {code}, Price: {exec_price:.2f}, Size: {exec_size}, Value: {exec_cost:.2f}, Comm: {exec_comm:.2f}, Date: {exec_date}')

                if data in self.active_trades:
                    pos = self.active_trades[data]
                    avg_entry_price = pos['avg_entry_price']
                    entry_date = pos['entry_date']

                    # Calculate PNL for this sold portion
                    # PNL = (Exit Value - Entry Cost for this portion) - Commission
                    # Entry Cost for this portion = avg_entry_price * exec_size
                    # Exit Value = exec_price * exec_size (or simply order.executed.value which is price*size)
                    # Note: order.executed.value is negative for sells, order.executed.cost is positive
                    entry_cost_portion = avg_entry_price * exec_size
                    pnl = (exec_price * exec_size - entry_cost_portion) - exec_comm # Simplified PNL calc
                    is_win = pnl > 0
                    dbg_trace(f"Sell calc: avg/{avg_entry_price}, size/{exec_size}, exec_price/{exec_price}")

                    # Record the completed portion
                    self.trading_history.append({
                        'code': code,
                        'entry_date': entry_date,
                        'exit_date': exec_date,
                        'avg_entry_price': avg_entry_price,
                        'exit_price': exec_price,
                        'size': exec_size, # Size of this specific sell
                        'pnl': pnl,
                        'is_win': is_win
                    })
                    dbg_trace(f"Recorded Trade Portion: {code}, Size: {exec_size}, PNL: {pnl:.2f}, Win: {is_win}")

                    # Update remaining position
                    pos['remaining_size'] -= exec_size
                    # Adjust total cost based on the cost removed (avg_entry_price * size_sold)
                    pos['total_cost'] -= entry_cost_portion

                    dbg_trace(f"Updated Active Trade {code}: Remaining Size: {pos['remaining_size']}, Remaining Cost: {pos['total_cost']:.2f}")


                    # Check if position is fully closed (handle potential float inaccuracies)
                    if pos['remaining_size'] == 0: # Consider position closed if remaining size is negligible
                        dbg_log(f"Closed Active Trade {code} fully.")
                        del self.active_trades[data]
                else:
                    # This might happen if selling logic triggers without a corresponding buy recorded
                    # or if handling short positions (not implemented here)
                    dbg_warning(f"Sell executed for {code} on {exec_date} but no active buy record found in self.active_trades.")

            # self.bar_executed = len(self) # This seems unnecessary unless used elsewhere

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            dbg_info('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None
    def stop(self):
        """
        Called at the end of the backtest. Calculate and print summary statistics.
        """
        # since we have analyzer, we don't print this out.
        return
        total_trades = len(self.trading_history)
        winning_trades = sum(1 for trade in self.trading_history if trade['is_win'])
        losing_trades = total_trades - winning_trades

        if total_trades > 0:
            win_rate = (winning_trades / total_trades) * 100
            total_pnl = sum(trade['pnl'] for trade in self.trading_history)

            dbg_info(f"--- Strategy Summary ---")
            dbg_info(f"Strategy Name: {self.NAME}")
            dbg_info(f"Total Trades: {total_trades}")
            dbg_info(f"Winning Trades: {winning_trades}")
            dbg_info(f"Losing Trades: {losing_trades}")
            dbg_info(f"Win Rate: {win_rate:.2f}%")
            dbg_info(f"Total PNL: {total_pnl:.2f}")
            dbg_info(f"------------------------\n")
        else:
            dbg_info(f"--- Strategy Summary ---")
            dbg_info(f"Strategy Name: {self.NAME}")
            dbg_info("No trades were executed.")
            dbg_info(f"------------------------\n")

        # You can also print the full trading history if needed
        # print("Trading History:")
        # for trade in self.trading_history:
        #     print(trade)
