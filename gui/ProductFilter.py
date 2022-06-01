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

class ProductFilter(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.mkt = Market()
        self.product_cb = None
        self.current_list = None

        ##############################################
        ##  Settings Grid
        ##############################################
        self.action_grid = Gtk.Grid()
        self.action_grid.set_margin_left(5)
        self.action_grid.set_margin_right(5)
        self.action_grid.set_margin_top(5)
        self.action_grid.set_margin_bottom(5)
        self.add(self.action_grid)


        ##  Category combo
        ##############################################
        # category_list = [
        #     "Customize 1",
        #     "Customize 2",
        #     "Customize 3",
        #     "Customize 4",
        #     "Customize 5",
        # ]
        category_list = self.mkt.get_industry_list()

        self.category_combo = Gtk.ComboBoxText()
        self.category_combo.set_entry_text_column(0)
        self.category_combo.connect("changed", self.on_list_combo_changed)
        for each_category in category_list:
            self.category_combo.append_text(each_category)

        self.action_grid.add(self.category_combo)


        ##  Customize List Button
        ##############################################
        self.add_to_list_button = Gtk.Button.new_with_label("Sync List")
        self.add_to_list_button.connect("clicked", self.on_sync_list_button)
        self.action_grid.add(self.add_to_list_button)

        self.add_to_list_button = Gtk.Button.new_with_label("+")
        self.add_to_list_button.connect("clicked", self.on_modify_list_button)
        self.action_grid.add(self.add_to_list_button)

        self.rm_from_list_button = Gtk.Button.new_with_label("-")
        self.rm_from_list_button.connect("clicked", self.on_modify_list_button)
        self.action_grid.add(self.rm_from_list_button)

        ##############################################
        ##  Product List
        ##############################################
        self.product_list = ProductList()
        self.add(self.product_list)

        # self.product_list.add_product("0050")
        # self.product_list.add_product("2330")
        # self.product_list.add_product("2603")
        # self.product_list.add_product("2454")
        # self.product_list.add_product("2727")
        # self.product_list.add_product("3714")
        # self.product_list.add_product("8069")
        ##############################################
        ##  Post Settings
        ##############################################
        # self.category_combo.set_active(0)
        # cat_list = self.mkt.get_product_list(industry=category_list[0])
        # # dbg_info("cat_list", cat_list, ",", category_list[0])
        # self.update_product_by_list(cat_list)

    def on_list_combo_changed(self, combo):
        # dbg_info("Combo:", combo)
        tree_iter = combo.get_active_iter()

        if tree_iter is not None:
            model = combo.get_model()
            # dbg_info(model[tree_iter])
            cat_name = model[tree_iter][0]
            target_list = self.mkt.get_product_list(industry=cat_name)
            self.product_list.rm_all_product()
            self.update_product_by_list(target_list)
        else:
            entry = combo.get_child()
            dbg_info("Entered: %s" % entry.get_text())
    def on_sync_list_button(self, widget, event=None):
        dbg_info("Sync Button")
        for each_prodcut in self.current_list:
            self.mkt.update_product_data(each_prodcut.code)

    def on_modify_list_button(self, widget, event=None):
        button_label = widget.get_label()
        dbg_info("Button:", button_label)
        if button_label == "1D":
            # self.chart_drawer.set_date(end_date=date.today(), 1)
            # self.chart_drawer.set_drawing_type('candle')
            pass
        elif button_label == "5D":
            self.chart_drawer.set_date(end_date=date.today(), duration=7)
            self.chart_drawer.set_drawing_type('candle')

    def refresh(self):
        # print("Refresh Chart " + self._var_stock_name)
        pass
    def update_product_by_list(self, target_list):
        self.current_list = target_list
        # dbg_info("Selected: len: ", len(target_list), target_list)
        for each_prodcut in target_list:
            # dbg_info("Add Product ", each_prodcut.code, "|", each_prodcut.name)

            # dbg_error("Remove update when doing filter")
            # self.mkt.update_product_data(each_prodcut.code)

            self.product_list.add_product(each_prodcut.code)
        self.product_list.refresh()
    def set_selected_cb(self, cb_func):
        self.product_cb = cb_func
        self.product_list.set_selected_cb(cb_func)
