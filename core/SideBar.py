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

class SideBarInfoBox:
    def __init__(self):
        self.side_bar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.side_bar_box.set_hexpand(False)

        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.search_entry = Gtk.SearchEntry()
        # self.search_entry.set_text("Search Code")

        search_box.pack_start(self.search_entry, False, True, 5)
        self.search_button = Gtk.Button.new_with_label("Search")

        search_box.pack_start(self.search_button, False, False, 5)
        self.side_bar_box.add(search_box)

        info_label = Gtk.Label(label="Infomation")
        info_label.set_halign(Gtk.Align.FILL)
        self.side_bar_box.pack_start(info_label, False, False, 0)

        info_frame = Gtk.Grid()
        info_frame.set_column_spacing(5)
        stock_name = Gtk.Label(label="Name")
        stock_name.set_halign(Gtk.Align.END)
        stock_name.set_halign(Gtk.Align.FILL)
        info_frame.attach(stock_name, 0, 0, 1, 1)


        # info_frame.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(0,0.1,0))

        self.stock_name_label = Gtk.Label(label="2454")
        self.stock_name_label.set_halign(Gtk.Align.END)
        self.stock_name_label.set_hexpand(bool(1))
        info_frame.attach(self.stock_name_label, 1, 0, 1, 1)

        # info_frame.set_margin_left(5)


        self.side_bar_box.pack_start(info_frame, True, True, 0)
    def get_main_layer(self):
        return self.side_bar_box
    def refresh(self):
        # print("Refresh ")
        self.stock_name_label.set_text(self.search_entry.get_text())
    def set_search_callback(self, cb_func):
        self.search_button.connect("clicked", cb_func)
        # self.search_entry.connect("stop-search", cb_func)
        # self.search_entry.connect("search-changed", cb_func)
        # self.search_button.connect("button-press-event", cb_func)
    # attr
    def set_product(self, product):
        self.stock_name_label.set_text(product.name)
        pass
    # def set_stock_name(self, stock_name):
    #     self.stock_name_label.set_text(stock_name)
    def get_search_entry(self):
        return self.search_entry.get_text()
    def get_stock_name(self):
        return self.stock_name_label.get_text()

