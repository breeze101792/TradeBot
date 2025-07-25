import math
import traceback
from typing import Type, Dict, Any, Optional, List
from datetime import datetime

from utility.debug import *
from core.config import AppConfigManager
from strategy.strategy import StrategyManager

from market.market import *
from trading.evaluate import Evaluate
from trading.traderecord import Recorder
from broker.brokermanager import BrokerManager
from broker.order.constant import OrderStatus, OrderAction, OrderPrice
from broker.order.event import Event
from broker.order.ordertracker import OrderTracker

# Note.
# BrokerManager.initialize() should be called externally before these methods.
# trade_broker.connect()/disconnect() # Removed as connection is managed by BrokerManager.initialize()/finalize()

class Trading:
    BUYING_IGNORE = False
    SELLING_IGNORE = False

    BUYING_CANDIDATE = dict()

    def __init__(self):
        # this will break mock on test case, if you want this mock before init.
        # self.cm = AppConfigManager()

        # for record open/close trade.
        # self.recorder = Recorder()
        bm = BrokerManager()
        bm.set_order_callback(self.order_callback)
    def order_callback(self, event: Event, data: Optional[Any] = None):
        """
        Callback function for handling events from the OrderService.
        This method processes different types of order-related events (e.g., OrderFilled, OrderFailed).

        Args:
            event (Event): The type of event that occurred.
            data (Optional[Any]): The data associated with the event, typically an `OrderTracker` object.
        """

        # recorder = Recorder()
        dbg_info(f"order_callback received event: {event}, data: {data}")

        if event == Event.OrderFilled:
            if not isinstance(data, OrderTracker):
                dbg_error(f"Event '{event}' received with invalid data type. Expected OrderTracker, got {type(data)}.")
                return
            
            # Data is an OrderTracker object
            order_tracker: OrderTracker = data
            recorder = Recorder()

            dbg_info(f"Order Filled: Symbol={order_tracker.symbol}, Action={order_tracker.action}, "
                        f"Size={order_tracker.size}, Price={order_tracker.price}, Commission={order_tracker.commission}.")

            # Log the transaction using data from the OrderTracker
            strategy_name = None
            if order_tracker.action == OrderAction.BUY:
                if order_tracker.symbol in Trading.BUYING_CANDIDATE:
                    strategy_name = Trading.BUYING_CANDIDATE[order_tracker.symbol]['strategy'].NAME
                else:
                    dbg_warning(f"Symbol {order_tracker.symbol} not in BUYING_CANDIDATE for a BUY order.")

            if strategy_name is None:
                # Fallback for BUYING not in candidate, or for SELLING
                # For SELL, the strategy should be part of the open trade record.
                # Passing a strategy here might be for opening trades only.
                # Let's use default as a fallback.
                stra_mgr = StrategyManager()
                strategy_name = stra_mgr.get_default_strategy().NAME
                dbg_info(f"Using default strategy for {order_tracker.symbol} ({order_tracker.action}).")

            # FIXME: The timestamp is not available in the order_tracker, use current time for now.
            recorder.add_record(
                symbol=order_tracker.symbol,
                action=order_tracker.action,
                price=order_tracker.price,
                size=order_tracker.size,
                timestamp=int(datetime.now().timestamp() * 1000),
                commission=order_tracker.commission,
                strategy=strategy_name
            )
        # currently, we don't need to handle any other event.
        # elif event == Event.OrderFailed:
        #     if not isinstance(data, OrderTracker):
        #         dbg_error(f"Event '{event}' received with invalid data type. Expected OrderTracker, got {type(data)}.")
        #         return
        #     order_tracker: OrderTracker = data
        #     dbg_warning(f"Order Failed: Symbol={order_tracker.symbol}, Action={order_tracker.action}, "
        #                 f"Size={order_tracker.size}, Reason={order_tracker.reason}.")
        #     # Optionally log failed orders or take other actions
        # elif event == Event.OrderPending:
        #     if not isinstance(data, OrderTracker):
        #         dbg_error(f"Event '{event}' received with invalid data type. Expected OrderTracker, got {type(data)}.")
        #         return
        #     order_tracker: OrderTracker = data
        #     dbg_info(f"Order Pending: Symbol={order_tracker.symbol}, Action={order_tracker.action}, "
        #                 f"Size={order_tracker.size}, Price={order_tracker.price}.")
        # elif event == Event.OrderCanceled:
        #     if not isinstance(data, OrderTracker):
        #         dbg_error(f"Event '{event}' received with invalid data type. Expected OrderTracker, got {type(data)}.")
        #         return
        #     order_tracker: OrderTracker = data
        #     dbg_info(f"Order Canceled: Symbol={order_tracker.symbol}, Order ID={order_tracker.order_id}, "
        #                 f"Reason={order_tracker.reason}.")
        # else:
        #     dbg_info(f"Unhandled event received: {event}, data: {data}")

    def buying_exec(self, buy_list):
        if self.BUYING_IGNORE is True:
            dbg_warning('Buying is on hold.')
            return True
        cfgmgr = AppConfigManager()
        LOT_UNIT = cfgmgr.get('stock.lot_unit')
        CASH_MAX_PER_TRADE = cfgmgr.get('stock.cash_max_per_trade')
        CASH_MIN_PER_TRADE = cfgmgr.get('stock.cash_min_per_trade')

        # {symbol:2330, price:1000, size:1000, }
        if len(buy_list) >= 1:
            # TODO, Place order & save to data base for info/stop_loss price.
            trade_broker = BrokerManager()
            for each_symbol in buy_list:
                try:
                    # NOTE. ignore holdings.
                    each_position = trade_broker.get_position_by_symbol(each_symbol)
                    if each_position is not None and each_position.size != 0:
                        dbg_debug(f"[{each_symbol}] Skipping buy evaluation: already holding position (size: {each_position.size}).")
                        continue

                    dbg_info(f'Buying product: {each_symbol}')
                    # 0.9 is to avoid market price increase cause insufficient funds.
                    current_cash = trade_broker.get_balance() * 0.9
                    # budget should smaller then CASH_MAX_PER_TRADE.
                    buying_budget = current_cash if current_cash < CASH_MAX_PER_TRADE else CASH_MAX_PER_TRADE
                    current_price = trade_broker.get_last_price(each_symbol, OrderPrice.ASK)
                    # sanity check
                    if current_price == None or current_price <= 0:
                        dbg_info(f'get price fail for {each_symbol}, ignore it.')
                        continue

                    # size should be the 1000x
                    order_lot = math.floor(buying_budget / (current_price * LOT_UNIT))
                    order_size = order_lot * LOT_UNIT

                    dbg_info(f'[{each_symbol}] price:{current_price}, order_size: {order_size}, budget: {buying_budget}/CASH_MIN_PER_TRADE')
                    # sanity check
                    if CASH_MIN_PER_TRADE <= current_price * order_size <= buying_budget:
                        trade_broker.place_order(symbol=each_symbol, size=order_size, action=OrderAction.BUY)
                    else:
                        dbg_warning(f'Insufficient cash (buget {buying_budget}), ignore buying product:{each_symbol} at size:{order_size}, price:{current_price}')
                except Exception as e:
                    dbg_error(e)
                
                    traceback_output = traceback.format_exc()
                    dbg_error(traceback_output)

            trade_broker.summarize_positions()
        else:
            dbg_info('ignore buying, len is 0.')

    def selling_exec(self, selling_list):
        if self.SELLING_IGNORE is True:
            dbg_warning('Selling is on hold.')
            return True
        # selling_list.append({
        #     'symbol': trade_info['symbol'],
        #     'size': trade_info['size'], # Sell the position size strategy decided.
        #     'price': trade_info['price'], # Target sell price from strategy (might be indicative)
        #     'strategy': target_strategy # Keep strategy object if needed later
        # })

        cfgmgr = AppConfigManager()
        CASH_MIN_PER_TRADE = cfgmgr.get('stock.cash_min_per_trade')

        if len(selling_list) >= 1:
            # TODO, Place order & save to data base for info/stop_loss price.
            trade_broker = BrokerManager()
            for each_symbol in selling_list:
                try:
                    symbol = each_symbol['symbol']
                    # DON"T need to times 1000
                    selling_size = each_symbol['size']

                    current_cash = trade_broker.get_balance()
                    current_price = trade_broker.get_last_price(symbol, OrderPrice.BID)
                    if current_price is None or current_price <= 0:
                        # FIXME, need notification to user.
                        dbg_warning(f"Can't get current price of {symbol} (returned None), ignore actions.")
                        continue
                    holding_size = trade_broker.get_position_by_symbol(symbol).size

                    dbg_info(f'Selling product: {symbol}, try selling {selling_size} from current hoding {holding_size}')
                    if current_price <= 0 or holding_size <= 0:
                        # FIXME, find another way to take actions.
                        dbg_warning("can't get current price of {symbol} or size {holding_size}, ignore actions.")
                        continue

                    elif selling_size == holding_size:
                        # close the trade.
                        trade_broker.place_order(symbol=symbol, size=selling_size, action=OrderAction.SELL)

                    elif selling_size < holding_size:
                        checking_size = selling_size if selling_size <= holding_size - selling_size else holding_size - selling_size
                        # if selling size smaller then hodling size, we check if it match the minimum trading cash.
                        if checking_size * current_price < CASH_MIN_PER_TRADE:
                            trade_broker.place_order(symbol=symbol, size=holding_size, action=OrderAction.SELL)
                            dbg_info(f'[{symbol}] remining/selling size will hit CASH_MIN_PER_TRADE, so we sell/close the trade.')
                        else:
                            # it's checked, sell with expecited size.
                            trade_broker.place_order(symbol=symbol, size=selling_size, action=OrderAction.SELL)

                    else:
                        # if selling size greater then hodling size, there is en error in it, but we just sell it all.
                        dbg_warning(f'[{symbol}] selling size({selling_size}) is greate then hoding size({holding_size}), set to hoding size.')
                        trade_broker.place_order(symbol=symbol, size=holding_size, action=OrderAction.SELL)
                except Exception as e:
                    dbg_error(e)
                
                    traceback_output = traceback.format_exc()
                    dbg_error(traceback_output)

            trade_broker.summarize_positions()
        else:
            dbg_info('ignore selling, len is 0.')

    def trading_eval(self, args = None, product_list = None):
        print(f"trading_eval: {args}")
        trade_eval = Evaluate()

        # Buyig evaluation, also override candidate.
        Trading.BUYING_CANDIDATE = trade_eval.buying_evaluation(product_list = product_list)

        return Trading.BUYING_CANDIDATE
    def selling_eval(self, args = None):
        trade_eval = Evaluate()

        # TODO, get pos list from broker.
        # pos_list = [{'code':'2330', 'position':5}] 
        trade_broker = BrokerManager()
        pos_list = trade_broker.get_all_positions()
        dbg_debug(f"Position: {pos_list.keys()}")

        # Selling evaluation.
        sell_list = trade_eval.selling_evaluation(pos_list)


        return sell_list
