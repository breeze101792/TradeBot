import math
import traceback
from utility.debug import *
from core.config import *

from market.market import *
from trading.evaluate import Evaluate
from broker.brokermanager import BrokerManager

class Trading:
    def __init__(self):
        self.cm = AppConfigManager()

    def buying_exec(self, buy_list):
        LOT_UNIT = self.cm.get('stock.lot_unit')
        CASH_PER_TRADE = self.cm.get('stock.cash_per_trade')

        # {symbol:2330, price:1000, size:1000, }
        if len(buy_list) >= 1:
            # TODO, Place order & save to data base for info/stop_loss price.
            trade_broker = BrokerManager()
            trade_broker.connect()
            for each_symbol in buy_list:
                try:
                    dbg_info(f'Buying product: {each_symbol}')
                    # 0.9 is to avoid market price increase cause insufficient funds.
                    current_cash = trade_broker.get_balance() * 0.9
                    # budget should smaller then CASH_PER_TRADE.
                    buying_budget = current_cash if current_cash < CASH_PER_TRADE else CASH_PER_TRADE
                    current_price = trade_broker.get_last_price(each_symbol)

                    # size should be the 1000x
                    order_lot = math.floor(buying_budget / (current_price * LOT_UNIT))
                    order_size = order_lot * LOT_UNIT

                    # sanity check
                    if current_price * order_size < buying_budget:
                        trade_broker.place_order(symbol=each_symbol, size=order_size, action='buy')
                    else:
                        dbg_warning(f'Insufficient cash (buget {buying_budget}), ignore buying product:{each_symbol} at size:{order_size}, price:{current_price}')
                except Exception as e:
                    dbg_error(e)
                
                    traceback_output = traceback.format_exc()
                    dbg_error(traceback_output)

            trade_broker.summarize_positions()
            trade_broker.disconnect()
        else:
            dbg_info('ignore buying, len is 0.')

    def selling_exec(self, selling_list):
        # selling_list.append({
        #     'symbol': trade_info['symbol'],
        #     'size': trade_info['size'], # Sell the position size strategy decided.
        #     'price': trade_info['price'], # Target sell price from strategy (might be indicative)
        #     'strategy': target_strategy # Keep strategy object if needed later
        # })

        if len( selling_list) >= 1:
            # TODO, Place order & save to data base for info/stop_loss price.
            trade_broker = BrokerManager()
            trade_broker.connect()
            for each_symbol in selling_list:
                try:
                    symbol = each_symbol['symbol']
                    # DON"T need to times 1000
                    selling_size = each_symbol['size']

                    dbg_info(f'Selling product: {symbol}')
                    current_cash = trade_broker.get_balance()
                    current_price = trade_broker.get_last_price(symbol)
                    holding_size = trade_broker.get_position_by_symbol(symbol).size
                    # size should be the 1000x

                    # sanity check
                    if selling_size <= holding_size:
                        trade_broker.place_order(symbol=symbol, size=selling_size, action='sell')
                    else:
                        dbg_warning(f'[{symbol}] selling size({selling_size}) is greate then hoding size({holding_size}), set to hoding size.')
                        trade_broker.place_order(symbol=symbol, size=holding_size, action='sell')
                except Exception as e:
                    dbg_error(e)
                
                    traceback_output = traceback.format_exc()
                    dbg_error(traceback_output)

            trade_broker.summarize_positions()
            trade_broker.disconnect()
        else:
            dbg_info('ignore selling, len is 0.')

    def trading_eval(self, args = None):
        trade_eval = Evaluate()

        # Buyig evaluation.
        buy_list = trade_eval.buying_evaluation()

        # NOTE. debug, don't not open it.
        # if self.cm.get('debug.development') is True: 
        #     self.__buying_exec(buy_list)
        # debug
        return buy_list
    def selling_eval(self, args = None):
        trade_eval = Evaluate()

        # TODO, get pos list from broker.
        # pos_list = [{'code':'2330', 'position':5}] 
        trade_broker = BrokerManager()
        trade_broker.connect()
        pos_list = trade_broker.get_all_positions()
        dbg_debug(f"Position: {pos_list.keys()}")

        # Selling evaluation.
        sell_list = trade_eval.selling_evaluation(pos_list)

        trade_broker.disconnect()

        return sell_list
