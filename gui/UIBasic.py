import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import matplotlib
matplotlib.use("GTK3Cairo")

#---------------------------
from gui.graphic.Drawer import *
from utility.debug import *
from market.Market import *
from gui.SideBar import *
from gui.MainChart import *
from gui.TabManager import *
from utility.debug import *

class UIBasic:
    def __init__(self):
        # self.product_change_cb_func = None
        self.current_product = None
        self.product_change_reciver_list = []
        dbg_info("init")

    def reg_product_change(self, reciver_func):
        if reciver_func is not None:
            self.product_change_reciver_list.append(reciver_func)
    def notify_product_change(self, product=None):
        if product is None:
            notify_product = self.current_product
        else:
            notify_product = product
        # calling upper layer function
        # self.product_change_cb_func(self, notify_product)
        dbg_info('product_list', self.product_change_reciver_list)
        for each_reciver in self.product_change_reciver_list:
            if each_reciver is not None:
                each_reciver(notify_product)
    @property
    def current_product(self):
        return self._current_product
    @current_product.setter
    def current_product(self, product):
        self._current_product = product
