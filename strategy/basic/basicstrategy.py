import backtrader as bt
import threading
from utility.debug import *
from core.config import AppConfigManager

# NOTE. strategy should only access by backtest class, so we could ensure the thread safty.
class BasicStrategy(bt.Strategy):
    # PreDefine
    DEBUG_FLAG = False
    LOT_UNIT = 1000
    MIN_CASH_PER_TRADE = 150000
    NAME="AdavanceStrategy"

    trading_date = None
    last_trade = {
        "date"          : None,
        "symbol"          : "",
        "action"        : "none", # sell/buy/None
        "price"         : 0,
        "size"      : 0,
    }

    # add initial order for testing.
    initial_order_history = []

    # recorder
    # Stores details of active buy positions:
    # {data: {'entry_date': date, 'avg_entry_price': float, 'remaining_size': int, 'total_cost': float}}
    active_trades = {}
    # Stores details of completed trade portions:
    # [{'code': str, 'entry_date': date, 'exit_date': date, 'avg_entry_price': float, 'exit_price': float, 'size': int, 'pnl': float, 'is_win': bool}]
    trading_history = []

    # This will not be inherited. just keep it as placeholder.
    params = (
    )

    def __init__(self):
        super().__init__()

        self.cm = AppConfigManager()
        self.LOT_UNIT = self.cm.get('stock.lot_unit')
        self.MIN_CASH_PER_TRADE = self.cm.get('stock.cash_min_per_trade')

        # we save the latest order, for checking if there is the duplicate order exist.
        # may need to modify it for mulitple order?
        self.order = None

        # reset status
        # self.reset_status(clean_all = False)
    def get_name(self):
        # get_name also include params to add more detail on it.
        param_dict = dict(vars(self.params))
        param_str = ''
        for param in param_dict.items():
            if param[0].startswith("_"):
                continue
            param_str += "_" + "".join(f"{each_word.upper().replace('_','')[0]}" for each_word in param[0].split('_'))

            if isinstance(param[1],float):
                # param_str += f"_{param[0][0]}{param[0][-1]}-{param[1]:.2f}"
                param_str += f"-{param[1]:.2f}"
            else:
                # param_str += f"_{param[0][0]}{param[0][-1]}-{param[1]}"
                param_str += f"-{param[1]}"


        # param_str = "_".join( f"{param[0][0]}{param[0][-1]}-{param[1]}" for param in param_dict.items() if not param[0].startswith("/"))

        return f"{self.NAME}{param_str}"
    def is_param(self, param_name: str) -> bool:
        """
        Check if a given string is one of the strategy's defined params.

        :param strategy_cls: A subclass of bt.Strategy
        :param param_name: The parameter name to check
        :return: True if param_name is in the strategy's params, else False
        """
        if not issubclass(self, bt.Strategy):
            raise TypeError("Provided class must be a subclass of bt.Strategy")
        
        param_names = [name for name, _ in self.params._getitems()]
        return param_name in param_names
    def dump_params(self):
        # get_name also include params to add more detail on it.
        param_dict = dict(vars(self.params))

        class_name = self.__class__.__name__
        print(f"Strategy: {class_name}")
        print("Params:")
        for k, v in param_dict.items():
            if not k.startswith('_'):  # Skip internal attrs like _getkwargs
                dbg_info(f"  {k} = {v}")

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
        dbg_trace(f"Reset strategy.{clean_all}")
        if clean_all is True:
            # this is for servive over cerebro.run()
            self.trading_date = None
            initial_order_history = []

            self.last_trade = {
                "date"          : None,
                "symbol"          : "",
                "action"        : "none", # sell/buy/None
                "price"         : 0,
                "size"      : 0,
            }
        # this is for calc winning rate.
        self.active_trades = {}
        # Stores details of completed trade portions:
        # [{'code': str, 'entry_date': date, 'exit_date': date, 'avg_entry_price': float, 'exit_price': float, 'size': int, 'pnl': float, 'is_win': bool}]
        self.trading_history = []
    def update_last_trading_info(self, date, code, action, price, size):
        # this function is for preserving last trading info.
        self.last_trade['date']          = date
        self.last_trade['symbol']          = code
        self.last_trade['action']        = action
        self.last_trade['price'] = price
        self.last_trade['size'] = size

        trade_info = self.last_trade
        dbg_trace(f"[{self.NAME}] Update Trade info {trade_info['symbol']}@{trade_info['date']}: Action: {trade_info['action']:<4}, Exec size: {trade_info['size']:>5}, Price: {trade_info['price']:>7.2f}")
    def notify_trade(self, trade):
        """
        Logs trade status changes (opened, closed).
        Detailed execution info is handled by notify_order.
        """
        trade_date = self.data.datetime.date(0) # Get date of the event
        code = trade.data._name if trade.data else 'N/A'

        if trade.justopened:
            dbg_trace(f'TRADE OPENED : {code}, Size: {trade.size}, Price: {trade.price:.2f}, Date: {trade_date}')
        elif trade.isclosed:
            dbg_trace(f'TRADE CLOSED : {code}, PNL: {trade.pnl:.2f}, PNL w/ Comm: {trade.pnlcomm:.2f}, Date: {trade_date}')
        # Optional: Log updates to existing trades if needed
        elif trade.isopen:
            dbg_trace(f'TRADE UPDATE : {code}, Current Size: {trade.size}, Date: {trade_date}')

    def notify_order(self, order):
        if order.status in [order.Completed, order.Canceled, order.Rejected]:
            self.order = None  # Reset after order is finalized

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
                dbg_trace(f'BUY EXECUTED: {code}, Price: {exec_price:.2f}, Size: {exec_size}, Comm: {exec_comm:.2f}, Date: {exec_date}')

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
                    # Removed dbg_trace for "Opened Active Trade" as info is in "BUY EXECUTED"
                    # NOTE. Because bt is next day trade, so it won't work on last day.
                    # Don't remove it, it's a important note.
                    # self.update_last_trading_info(
                    #     date=data.datetime.date(0),
                    #     code=data._name,
                    #     action="buy",
                    #     price=exec_price,
                    #     size=exec_size,
                    # )

            elif order.issell():
                # when sell, exec_size shows negative number
                exec_size = -exec_size
                dbg_trace(f'SELL EXECUTED: {code}, Price: {exec_price:.2f}, Size: {exec_size}, Comm: {exec_comm:.2f}, Date: {exec_date}')

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
                    # Removed dbg_trace for "Sell calc" as it's too detailed

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
                    # dbg_trace(f"Recorded Trade Portion: {code}, Size: {exec_size}, PNL: {pnl:.2f}, Win: {is_win}")

                    # Update remaining position
                    pos['remaining_size'] -= exec_size
                    # Adjust total cost based on the cost removed (avg_entry_price * size_sold)
                    pos['total_cost'] -= entry_cost_portion

                    dbg_trace(f"Updated Active Trade {code}: Remaining Size: {pos['remaining_size']}, Remaining Cost: {pos['total_cost']:.2f}")

                    # Check if position is fully closed (handle potential float inaccuracies)
                    if pos['remaining_size'] == 0: # Consider position closed if remaining size is negligible
                        dbg_trace(f"Closed Active Trade {code} fully with profit {pnl / entry_cost_portion:.2%}.")
                        # Assume -5% to stop lose, so -5% + (10%) will be max.
                        # the backtrader will sell the stock after you make the decidsion. so it may loos 10% more.
                        if pnl / entry_cost_portion < -0.15:
                            if self.trading_history: # Ensure trading_history is not empty
                                trade_details = self.trading_history[-1]
                                dbg_warning(f"PNL smaller then -10% ({pnl / entry_cost_portion:.2%})"
                                            f"Loss Trade Details: Code: {trade_details['code']}, "
                                            f"Entry: {trade_details['entry_date']} @{trade_details['avg_entry_price']:.2f}, "
                                            f"Exit: {trade_details['exit_date']} @{trade_details['exit_price']:.2f}, "
                                            f"Size: {trade_details['size']}, PNL: {trade_details['pnl']:.2f}")
                            else:
                                dbg_warning(f"PNL smaller then -10% ({pnl / entry_cost_portion:.2%}). code:{code}, entry_date: {entry_date}, exec_date: {exec_date}")

                        del self.active_trades[data]
                else:
                    # This might happen if selling logic triggers without a corresponding buy recorded
                    # or if handling short positions (not implemented here)
                    dbg_warning(f"Sell executed for {code} on {exec_date} size:{exec_size} but no active buy record found in active_trades: {self.active_trades}.")

                # NOTE. Because bt is next day trade, so it won't work on last day.
                # Don't remove it, it's a important note.
                # self.update_last_trading_info(
                #     date=data.datetime.date(0),
                #     code=data._name,
                #     action="sell",
                #     price=exec_price,
                #     size=exec_size,
                # )

            # self.bar_executed = len(self) # This seems unnecessary unless used elsewhere

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            dbg_warning(f'!!! Order for {order.data._name} Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None
    def start(self):
        # WARNING: Acquiring lock here and holding until stop() can be risky.
        # Ensure stop() is always called to release the lock, even on errors.

        # clear status.
        self.reset_status(clean_all = False)

        # Format: tuple of tuples -> ((datetime, size, price, data_name),)
        data_pos_idx = 1
        data_price_idx = 2
        data_name_idx = 3

        if self.trading_date is not None:
            if self.trading_date != self.datas[0].datetime.date(0):
                dbg_error(f"Trading date mismatch. Expected: {self.trading_date}, Got: {self.datas[0].datetime.date(0)}")
                raise ValueError("Trading date mismatch during strategy start.")

        if self.initial_order_history is None or len(self.initial_order_history) == 0:
            dbg_debug('No order history found.')
            return
        if self.initial_order_history is None or len(self.initial_order_history) == 0:
            dbg_debug('No order history found.')
            return
        for data in self.datas:
            for each_record in self.initial_order_history:
                # FIXME, insufficent fund will cause update fail without any notification.
                if each_record[data_name_idx] == data._name:
                    price = each_record[data_price_idx]

                    # [--
                    self.stop_loss[data] = price * (1 - self.params.trailing_stop_pct)  # Set initial stop loss (5% down)
                    self.take_profit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Set initial take profit (20% up)

                    self.trailing_stop[data] = price * (1 - self.params.trailing_stop_pct)  # Set initial trailing stop loss (5% down)
                    self.trailing_takeprofit[data] = price * (1 + self.params.trailing_takeprofit_pct)  # Set initial trailing take profit (20% up)
                    # --]

                    dbg_trace(f"Add order history of {data._name}, pos:{each_record[data_pos_idx]}/price:{each_record[data_price_idx]}")

                    self.initial_order_history.remove(each_record)
                else:
                    dbg_warning(f"{data._name}/{each_record[data_name_idx]}(recorded data is wrong?) are different.")

        # FIXME, if the con-current exist, this will cause issue. don't mix up buy/sell thread.
        if len(self.initial_order_history) != 0:
            dbg_error(f"initial_order_history init fail {self.initial_order_history}.")
            raise
        else:
            self.initial_order_history = []
        # Lock acquired in start() is held until stop()

    def stop(self):
        """
        Called at the end of the backtest. Calculate and print summary statistics.
        """
        # since we have analyzer, we don't print this out.
        # return # Commented out return to allow lock release below

        total_trades = len(self.trading_history)
        winning_trades = sum(1 for trade in self.trading_history if trade['is_win'])
        losing_trades = total_trades - winning_trades

        if total_trades > 0:
            win_rate = (winning_trades / total_trades) * 100
            total_pnl = sum(trade['pnl'] for trade in self.trading_history)

            dbg_trace(f"--- Strategy Summary ---")
            dbg_trace(f"Strategy Name: {self.NAME}")
            dbg_trace(f"Total Trades: {total_trades}")
            dbg_trace(f"Winning Trades: {winning_trades}")
            dbg_trace(f"Losing Trades: {losing_trades}")
            dbg_trace(f"Win Rate: {win_rate:.2f}%")
            dbg_trace(f"Total PNL: {total_pnl:.2f}")
            dbg_trace(f"------------------------")
        else:
            dbg_trace(f"--- Strategy Summary ---")
            dbg_trace(f"Strategy Name: {self.NAME}")
            dbg_trace("No trades were executed.")
            dbg_trace(f"------------------------")

        if self.last_trade and self.last_trade['date'] is not None:
            dbg_trace(f"Last Trade Info: {self.last_trade}")

        # List out any open trades if they exist
        if self.active_trades:
            dbg_trace(f"--- Open Trades at Stop ---")
            for data, pos in self.active_trades.items():
                dbg_trace(f"  Code: {data._name}, Entry Date: {pos['entry_date']}, Avg Entry Price: {pos['avg_entry_price']:.2f}, Remaining Size: {pos['remaining_size']}")
            dbg_trace(f"---------------------------")
        else:
            dbg_trace(f"--- Open Trades at Stop ---")
            dbg_trace("No open trades at the end of backtest.")
            dbg_trace(f"---------------------------")

        # You can also print the full trading history if needed
        # print("Trading History:")
        # for trade in self.trading_history:

    def sell(self, data, size, *args, **kwargs):
        # FIXME, use close as price.
        price = data.close[0]
        dbg_trace(f'Sell {data._name}, size:{size}')
        self.update_last_trading_info(
            date=data.datetime.date(0),
            code=data._name,
            action="sell",
            price=price,
            size=size,
        )
        if self.order is not None:
            dbg_warning(f"Cancelling existing order for {self.order.data._name}: Ref: {self.order.ref}, Type: {'Buy' if self.order.isbuy() else 'Sell'}, Size: {self.order.size}, Price: {self.order.price}, Status: {self.order.getstatusname()}")
            self.order.cancel()
        self.order = super().sell(data=data, size=size, *args, **kwargs)
        return self.order
    def buy(self, data, size, *args, **kwargs):
        # FIXME, use close as price.
        price = data.close[0]
        dbg_trace(f'Buy {data._name}, size:{size}')
        self.update_last_trading_info(
            date=data.datetime.date(0),
            code=data._name,
            action="buy",
            price=price,
            size=size,
        )
        # if self.order is not None:
        #     dbg_warning(f"Cancelling existing order for {self.order.data._name}: Ref: {self.order.ref}, Type: {'Buy' if self.order.isbuy() else 'Sell'}, Size: {self.order.size}, Price: {self.order.price}, Status: {self.order.getstatusname()}")
        #     self.order.cancel()

        self.order = super().buy(data=data, size=size, *args, **kwargs)
        return self.order

class BasicExitStrategy(BasicStrategy):
    def stra_initial(self):
        raise NotImplementedError("Subclasses must implement this method.")
    def stra_buy_in(self, data):
        raise NotImplementedError("Subclasses must implement this method.")
    def stra_sell_out(self, data):
        raise NotImplementedError("Subclasses must implement this method.")

