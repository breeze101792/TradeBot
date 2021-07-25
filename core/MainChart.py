import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
import matplotlib
matplotlib.use("GTK3Cairo")
#---------------------------
from graphic.Drawer import *
from utility.debug import *
from market.Market import *
from core.SideBar import *

class MainChart:
    def __init__(self):
        self._var_stock_name = str()
        self.box_main_chart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # label_title = Gtk.Label(label="Graphic Chart")
        # self.box_main_chart.pack_start(label_title, False, False, 0)

        self.chart_drawer = Drawer()
        self.box_main_chart.pack_start(self.chart_drawer.get_canvas(), True, True, 4)

    def refresh(self):
        # print("Refresh Chart " + self._var_stock_name)
        self.chart_drawer.refresh()
    def set_product(self, product):
        self.product = product
        self.chart_drawer.set_product(product)

    def get_main_layer(self):
        return self.box_main_chart
    # # attr
    # @property
    # def var_stock_name(self):
    #     return self._var_stock_name
    # @var_stock_name.setter
    # def var_stock_name(self, value):
    #     print("Setter " + value)
    #     self._var_stock_name = value

