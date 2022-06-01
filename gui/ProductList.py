import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
#---------------------------
from gui.MainChart import *
from market.Market import *
from gui.InfoChart import *
from utility.debug import *

class ProductList(Gtk.FlowBox):
    def __init__(self):
        ##############################################
        ## Preset Set
        ##############################################
        super().__init__()
        self.info_chart_list = []
        self.mkt = Market()
        self.set_homogeneous(True)
        self.product_cb = None

        self.set_valign(Gtk.Align.START)
        # self.set_max_children_per_line(30)
        # self.set_selection_mode(Gtk.SelectionMode.NONE)
        self.connect('child-activated', self.__on_selected_cb)

        ##############################################
        ## Preset Set
        ##############################################
        # self.add_product("0050")
        # self.add_product("2330")
        # self.add_product("2603")
        # self.add_product("2454")
        # self.add_product("2727")
        # self.add_product("3714")
        # self.add_product("8069")

    def add_product(self, product_code):
        for each_product in self.info_chart_list:
            if each_product.get_product_code() == product_code:
                dbg_info("Product exist in info chart list\n")
                return True

        product_ins = self.mkt.get_product(product_code)
        info_char = InfoChart()
        info_char.set_product(product_ins)
        info_char.refresh()

        # dbg_info("Add Product: ", product_ins.code ,"|", product_ins.name)
        self.info_chart_list.append(info_char)
        self.add(info_char.get_main_layer())
        # self.pack_start(info_char.get_main_layer(), True, True, 4)


    def rm_product(self, product_code):
        pass
    def rm_all_product(self):
        size_of_list = len(self.info_chart_list)

        for product_idx in range(0, size_of_list):
            # dbg_info("remove product:", size_of_list, self.info_chart_list[product_idx])
            self.remove(self.info_chart_list[product_idx].get_main_layer().get_parent())
        # self.info_chart_list.remove(self.info_chart_list[product_idx])
        self.info_chart_list = []

        # for each_product in self.info_chart_list:
        #     # dbg_info(each_product)
        #     self.remove(each_product.get_main_layer().get_parent())
        #     self.info_chart_list.remove(each_product)

    def refresh(self):
        self.show_all()
    def __on_selected_cb(self, widget, event=None):
        if self.product_cb is not None:
            child_idx = self.get_selected_children()[0].get_index()
            dbg_info("on_selected_cb, (%s, %s)" % (len(self.get_selected_children()).__str__(), child_idx.__str__()))
            self.product_cb(self.info_chart_list[child_idx].get_product() , event)
    def set_selected_cb(self, cb_func):
        self.product_cb = cb_func


    # def set_product(self, product):
    #     self.current_product = product
