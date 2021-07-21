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
        self.current_product = None

        ##############################################
        ## Container
        ##############################################
        self.side_bar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.side_bar_box.set_hexpand(False)

        ##############################################
        ## Search Box
        ##############################################
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.search_entry = Gtk.SearchEntry()
        # self.search_entry.set_text("Search Code")

        search_box.pack_start(self.search_entry, False, True, 5)
        self.search_button = Gtk.Button.new_with_label("Search")

        search_box.pack_start(self.search_button, False, False, 5)
        self.side_bar_box.add(search_box)

        ##############################################
        ## Info Frame
        ##############################################
        info_frame = Gtk.Frame()
        info_frame.set_label("Product Info")
        self.side_bar_box.pack_start(info_frame, True, True, 0)

        info_grid = Gtk.Grid()
        info_grid.set_column_spacing(5)
        # info_grid.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(0,0.1,0))
        info_frame.add(info_grid)
        grid_idx = 0

        product_name = Gtk.Label(label="Name")
        product_name.set_halign(Gtk.Align.END)
        product_name.set_halign(Gtk.Align.FILL)
        info_grid.attach(product_name, 0, grid_idx, 1, 1)

        self.product_name_label = Gtk.Label(label="")
        self.product_name_label.set_halign(Gtk.Align.END)
        self.product_name_label.set_hexpand(bool(1))
        info_grid.attach(self.product_name_label, 1, grid_idx, 1, 1)
        grid_idx = grid_idx + 1

        #------------------------------------------------
        industry_name = Gtk.Label(label="Industry")
        industry_name.set_halign(Gtk.Align.END)
        industry_name.set_halign(Gtk.Align.FILL)
        info_grid.attach(industry_name, 0, grid_idx, 1, 1)

        self.industry_name_label = Gtk.Label(label="")
        self.industry_name_label.set_halign(Gtk.Align.END)
        self.industry_name_label.set_hexpand(bool(1))
        info_grid.attach(self.industry_name_label, 1, grid_idx, 1, 1)
        grid_idx = grid_idx + 1

        #------------------------------------------------
        market_name = Gtk.Label(label="Market")
        market_name.set_halign(Gtk.Align.END)
        market_name.set_halign(Gtk.Align.FILL)
        info_grid.attach(market_name, 0, grid_idx, 1, 1)

        self.market_name_label = Gtk.Label(label="")
        self.market_name_label.set_halign(Gtk.Align.END)
        self.market_name_label.set_hexpand(bool(1))
        info_grid.attach(self.market_name_label, 1, grid_idx, 1, 1)
        grid_idx = grid_idx + 1

        ##############################################
        ## Analysis Frame
        ##############################################
        analysis_frame = Gtk.Frame()
        analysis_frame.set_label("Analysis Info")
        self.side_bar_box.pack_start(analysis_frame, True, True, 0)

        analysis_grid = Gtk.Grid()
        analysis_grid.set_column_spacing(5)
        # analysis_grid.modify_bg(Gtk.StateType.NORMAL, Gdk.Color(0,0.1,0))
        analysis_frame.add(analysis_grid)
        grid_idx = 0

        #------------------------------------------------
        five_day_price_name = Gtk.Label(label="5 Day Price")
        five_day_price_name.set_halign(Gtk.Align.END)
        five_day_price_name.set_halign(Gtk.Align.FILL)
        analysis_grid.attach(five_day_price_name, 0, grid_idx, 1, 1)

        self.five_day_price_label = Gtk.Label(label="NA")
        self.five_day_price_label.set_halign(Gtk.Align.END)
        self.five_day_price_label.set_hexpand(bool(1))
        analysis_grid.attach(self.five_day_price_label, 1, grid_idx, 1, 1)
        grid_idx = grid_idx + 1

        #------------------------------------------------
        ten_day_price_name = Gtk.Label(label="10 Day Price")
        ten_day_price_name.set_halign(Gtk.Align.END)
        ten_day_price_name.set_halign(Gtk.Align.FILL)
        analysis_grid.attach(ten_day_price_name, 0, grid_idx, 1, 1)

        self.ten_day_price_label = Gtk.Label(label="NA")
        self.ten_day_price_label.set_halign(Gtk.Align.END)
        self.ten_day_price_label.set_hexpand(bool(1))
        analysis_grid.attach(self.ten_day_price_label, 1, grid_idx, 1, 1)
        grid_idx = grid_idx + 1

    def get_main_layer(self):
        return self.side_bar_box
    def refresh(self):
        self.update_info_frame()
    def set_search_callback(self, cb_func):
        self.search_button.connect("clicked", cb_func)
        # self.search_entry.connect("stop-search", cb_func)
        # self.search_entry.connect("search-changed", cb_func)
        # self.search_button.connect("button-press-event", cb_func)
    ## Update
    def update_info_frame(self):
        if self.current_product is None:
            return
        self.product_name_label.set_text(self.current_product.code + "(" + self.current_product.name + ")")
        self.industry_name_label.set_text(self.current_product.industry)
        self.market_name_label.set_text(self.current_product.market + "(" + self.current_product.type + ")")
    # attr
    def set_product(self, product):
        self.current_product = product
        # self.product_name_label.set_text(product.name)
    def get_search_entry(self):
        return self.search_entry.get_text()
    def get_stock_name(self):
        return self.product_name_label.get_text()

