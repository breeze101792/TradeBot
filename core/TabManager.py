import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
#---------------------------
from core.MainChart import *
from utility.debug import *
from core.ProductList import *
from core.ProductFilter import *

class TabManager():
    def __init__(self):
        self.current_product = None
        self.nb = Gtk.Notebook()

        ##############################################
        ## Chart Page
        ##############################################
        self.main_chart = MainChart()
        self.nb.append_page(self.main_chart.get_main_layer())
        self.nb.set_tab_label_text(self.main_chart.get_main_layer(), "Chart")

        ###############################################
        ### Product Page
        ###############################################
        self.product_list = ProductList()
        #self.nb.append_page(self.product_list)
        #self.nb.set_tab_label_text(self.product_list, "Product List")

        #self.product_list.add_product("0050")
        #self.product_list.add_product("2330")
        #self.product_list.add_product("2603")
        #self.product_list.add_product("2454")
        #self.product_list.add_product("2727")
        #self.product_list.add_product("3714")
        #self.product_list.add_product("8069")

        ##############################################
        ## Filter Page
        ##############################################
        self.product_filter = ProductFilter()
        self.nb.append_page(self.product_filter)
        self.nb.set_tab_label_text(self.product_filter, "Filter")

        ##############################################
        ## Update Page
        ##############################################
        self.update_place_holder = Gtk.Box()
        self.nb.append_page(self.update_place_holder)
        self.nb.set_tab_label_text(self.update_place_holder, "Update")

    def refresh(self):
        self.main_chart.refresh()

    def set_product(self, product):
        self.current_product = product
        self.main_chart.set_product(self.current_product)

    def get_main_layer(self):
        return self.nb
    def set_event_cb(self, cb_func):
        self.product_list.set_selected_cb(cb_func)
        self.product_filter.set_selected_cb(cb_func)
