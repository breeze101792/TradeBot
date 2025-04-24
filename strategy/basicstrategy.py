import backtrader as bt
from utility.debug import *

# class BasicStrategy(bt.Strategy):
#     NAME="BasicStrategy"
#     def reset_status(self):
#         pass
class BasicStrategy(bt.Strategy):
    NAME="AdavanceStrategy"
    trading_date = None
    last_trade = {
        "date"          : None,
        "code"          : "",
        "action"        : "none", # sell/buy/None
        "price"         : 0,
        "size"      : 0,
    }

    # add initial order for testing.
    initial_order_history = None

    # recorder
    # Stores details of active buy positions:
    # {data: {'entry_date': date, 'avg_entry_price': float, 'remaining_size': int, 'total_cost': float}}
    active_trades = {}
    # Stores details of completed trade portions:
    # [{'code': str, 'entry_date': date, 'exit_date': date, 'avg_entry_price': float, 'exit_price': float, 'size': int, 'pnl': float, 'is_win': bool}]
    trading_history = []
    def __init__(self):
        super().__init__()

        # reset status
        # self.reset_status(clean_all = False)
    def is_trading_date(self, data_date):
        if self.trading_date is None:
            return True
        if data_date == self.trading_date:
            # Your trading logic here
            # print("Running strategy logic on", self.datas[0].datetime.date(0))
            return True
        else:
            return False
    def reset_status(self, clean_all = False):
        if clean_all is True:
            # this is for servive over cerebro.run()
            self.trading_date = None
            self.last_trade = {
                "date"          : None,
                "code"          : "",
                "action"        : "none", # sell/buy/None
                "price"         : 0,
                "size"      : 0,
            }
            initial_order_history = None

        # this is for calc winning rate.
        self.active_trades = {}
        # Stores details of completed trade portions:
        # [{'code': str, 'entry_date': date, 'exit_date': date, 'avg_entry_price': float, 'exit_price': float, 'size': int, 'pnl': float, 'is_win': bool}]
        self.trading_history = []
    def update_trading_info(self, date, code, action, price, size):
        self.last_trade['date']          = date
        self.last_trade['code']          = code
        self.last_trade['action']        = action
        self.last_trade['price'] = price
        self.last_trade['size'] = size

        trade_info = self.last_trade
        dbg_trace(f"[{self.NAME}] Update Trade info {trade_info['code']}@{trade_info['date']}: Action: {trade_info['action']:<4}, Exec size: {trade_info['size']:>5}, Price: {trade_info['price']:>7.2f}")
    # def notify_trade(self, trade):
    #     """
    #     Logs trade status changes (opened, closed).
    #     Detailed execution info is handled by notify_order.
    #     """
    #     trade_date = bt.num2date(trade.dt).date() if trade.dt else None # Get date of the event
    #     code = trade.data._name if trade.data else 'N/A'
    #
    #     if trade.justopened:
    #         dbg_info(f'TRADE OPENED : {code}, Size: {trade.size}, Price: {trade.price:.2f}, Date: {trade_date}')
    #     elif trade.isclosed:
    #         dbg_info(f'TRADE CLOSED : {code}, PNL: {trade.pnl:.2f}, PNL w/ Comm: {trade.pnlcomm:.2f}, Date: {trade_date}')
    #     # Optional: Log updates to existing trades if needed
    #     # elif trade.isopen:
    #     #     dbg_trace(f'TRADE UPDATE : {code}, Current Size: {trade.size}, Date: {trade_date}')

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # dbg_trace('Buy/Sell order submitted/accepted to/by broker')
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
    def start(self):
        # clear status.
        self.reset_status(clean_all = False)

        # Format: tuple of tuples -> ((datetime, size, price, data_name),)
        data_pos_idx = 1
        data_price_idx = 2
        data_name_idx = 3

        if self.initial_order_history is None:
            dbg_debug('No order history found.')
            return
        for data in self.datas:
            for each_record in self.initial_order_history:
                if each_record[data_name_idx] == data._name:
                    price = each_record[data_price_idx]

                    # [--
                    self.stop_loss[data] = price * (1 - self.params.trailing_stop_pct)  # Set initial stop loss (5% down)
                    self.take_profit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Set initial take profit (20% up)

                    self.trailing_stop[data] = price * (1 - self.params.trailing_stop_pct)  # Set initial trailing stop loss (5% down)
                    self.trailing_takeprofit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Set initial trailing take profit (20% up)
                    # --]

                    dbg_info(f"Add order history of {data._name}, pos:{each_record[data_pos_idx]}/price:{each_record[data_price_idx]}")

                    self.initial_order_history.remove(each_record)
        if len(self.initial_order_history) != 0:
            dbg_error(f"initial_order_history init fail {self.initial_order_history}.")
            raise
        else:
            self.initial_order_history = None

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

    def sell(self, data, size):
        # FIXME, use close as price.
        price = data.close[0]
        # dbg_info(f'Sell {data._name}, size:{size}')
        self.update_trading_info(
            date=data.datetime.date(0),
            code=data._name,
            action="sell",
            price=price,
            size=size,
        )
        result = super().sell(data=data, size=size)
        return result
    def buy(self, data, size):
        # FIXME, use close as price.
        price = data.close[0]
        # dbg_info(f'Buy {data._name}, size:{size}')
        self.update_trading_info(
            date=data.datetime.date(0),
            code=data._name,
            action="buy",
            price=price,
            size=size,
        )
        result = super().buy(data=data, size=size)
        return result
