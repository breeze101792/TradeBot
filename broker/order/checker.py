from core.config import AppConfig
from broker.order.constant import OrderAction

# It's a unify size/price checker, this check is for safty reson.
# Always do it before place order. This is the 2nd safty.
class OrderChecker:
    # Use twise times of per trad max for our limit.
    CASH_LIMIT_PER_ORDER = AppConfig.stock.cash_max_per_trade * 2

    @staticmethod
    def check(action, price, size):
        # TODO, impl daily check limit. We limit the api usage for control daily  buy.
        if action == OrderAction.BUY and price * size > OrderChecker.CASH_LIMIT_PER_ORDER:
            reason = f"order reject by size checker, size: {size}, price:{price}"
            dbg_info(reason)
            raise ValueError
        return True
