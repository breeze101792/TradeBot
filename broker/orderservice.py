import threading
from queue import Queue
from utility.debug import * # Replace standard logging with custom debug system
from broker.ordertracker import OrderTracker
from broker.event import Event, default_event_callback
from typing import Callable
import time

class OrderService(threading.Thread):
    def __init__(self, broker_ins, event_callback: Callable[[Event, ...], None] = None): # Removed unused order_queue
        super().__init__(daemon=True)
        self.broker_ins = broker_ins # Corrected typo: broker_ini -> broker_ins
        self.running = True
        self.active_orders = []  # Track all active OrderTracker objects

        if event_callback is not None:
            self.event_callback = event_callback
        else:
            self.event_callback = default_event_callback

    def add_order(self, order_tracker: OrderTracker):
        # Add the OrderTracker object to the list of active orders for tracking.
        # check before we added it.
        status = order_tracker.status
        if status in ("filled"):
            dbg_trace(f"OrderService: Order {order_tracker} status changed to {status}, call back now.")
            self.event_callback(Event.OrderFilled, order_tracker)
        elif status in ("cancelled", "rejected", "failed"):
            dbg_trace(f"OrderService: Order {order_tracker} status changed to {status}, call back now.")
            self.event_callback(Event.OrderFailed, order_tracker)
        else:
            self.active_orders.append(order_tracker)
            dbg_debug(f"OrderService: Added order tracker for order ID {order_tracker.symbol} to active tracking. Status: {status}")

    def run(self):
        dbg_info('start running order service.')
        while self.running:
            new_active_orders = []
            # Poll all active orders
            for order_tracker in self.active_orders:
                try:
                    self.broker_ins.update_order_status(order_tracker)
                    dbg_debug(f"Order {order_tracker} status: {status}")
                    status = order_tracker.status

                    if status in ("filled"):
                        dbg_info(f"OrderService: Order {order_tracker} status changed to {status}, removed from tracking.")
                        self.event_callback(Event.OrderFilled, order_tracker)
                    elif status in ("cancelled", "rejected"):
                        dbg_info(f"OrderService: Order {order_tracker} status changed to {status}, removed from tracking.")
                        self.event_callback(Event.OrderFailed, order_tracker)
                    else:
                        new_active_orders.append(order_tracker) # Keep tracking

                except Exception as e:
                    dbg_error(f"OrderService: Error updating status for order {order_tracker}: {e}")
                    new_active_orders.append(order_tracker) # Keep tracking if error, maybe retry later

            self.active_orders = new_active_orders # Update the list of active orders
            time.sleep(1)  # Polling interval

    def stop(self):
        self.running = False
        dbg_debug("OrderService: Stopping order tracking thread.")

