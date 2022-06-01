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

class MainChart:
    def __init__(self):
        self._var_stock_name = str()
        self.box_main_chart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # label_title = Gtk.Label(label="Graphic Chart")
        # self.box_main_chart.pack_start(label_title, False, False, 0)

        ##############################################
        ##  Settings Frame
        ##############################################
        analysis_frame = Gtk.Frame()
        analysis_frame.set_label("Settings")
        analysis_frame.set_margin_left(32)
        analysis_frame.set_margin_right(32)
        # analysis_frame.set_border_width(5)
        # analysis_frame.set_label_align(1,1)
        self.box_main_chart.pack_start(analysis_frame, False, True, 5)

        self.setting_grid = Gtk.Grid()
        self.setting_grid.set_margin_left(5)
        self.setting_grid.set_margin_right(5)
        self.setting_grid.set_margin_top(5)
        self.setting_grid.set_margin_bottom(5)
        # self.box_main_chart.pack_start(self.setting_grid, False, False, 5)
        analysis_frame.add(self.setting_grid)

        self.real_time_button = Gtk.Button.new_with_label("RT")
        self.real_time_button.connect("clicked", self.on_range_button)
        # self.box_main_chart.pack_start(self.real_time_button, False, False, 5)
        self.setting_grid.add(self.real_time_button)

        # self.fine_day_button = Gtk.Button.new_with_label("5D")
        # self.fine_day_button.connect("clicked", self.on_range_button)
        # # self.box_main_chart.pack_start(self.fine_day_button, False, False, 5)
        # self.setting_grid.add(self.fine_day_button)

        self.one_month_button = Gtk.Button.new_with_label("1M")
        self.one_month_button.connect("clicked", self.on_range_button)
        # self.box_main_chart.pack_start(self.one_month_button, False, False, 5)
        self.setting_grid.add(self.one_month_button)

        self.three_month_button = Gtk.Button.new_with_label("3M")
        self.three_month_button.connect("clicked", self.on_range_button)
        # self.box_main_chart.pack_start(self.three_month_button, False, False, 5)
        self.setting_grid.add(self.three_month_button)

        self.six_month_button = Gtk.Button.new_with_label("6M")
        self.six_month_button.connect("clicked", self.on_range_button)
        # self.box_main_chart.pack_start(self.six_month_button, False, False, 5)
        self.setting_grid.add(self.six_month_button)

        self.one_year_button = Gtk.Button.new_with_label("1Y")
        self.one_year_button.connect("clicked", self.on_range_button)
        # self.box_main_chart.pack_start(self.one_year_button, False, False, 5)
        self.setting_grid.add(self.one_year_button)

        self.five_year_button = Gtk.Button.new_with_label("5Y")
        self.five_year_button.connect("clicked", self.on_range_button)
        # self.box_main_chart.pack_start(self.five_year_button, False, False, 5)
        self.setting_grid.add(self.five_year_button)

        self.max_button = Gtk.Button.new_with_label("Max")
        self.max_button.connect("clicked", self.on_range_button)
        # self.box_main_chart.pack_start(self.max_button, False, False, 5)
        self.setting_grid.add(self.max_button)

        ##############################################
        ## Main Drawer
        ##############################################
        self.chart_drawer = Drawer()
        self.box_main_chart.pack_start(self.chart_drawer.get_canvas(), True, True, 4)

        # scroll bar
        self.time_adjustment = Gtk.Adjustment(100, 0, 100, 10, 20, 0)
        self.time_adjustment.connect("value-changed", self.on_time_adjustment_change)
        hscrollbar = Gtk.Scrollbar(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.time_adjustment)
        self.box_main_chart.pack_start(hscrollbar, False, False, 4)
    def on_time_adjustment_change(self, widget, event=None):
        # dbg_info("Value: ", widget.get_value())
        self.chart_drawer.set_date_by_percentage(widget.get_value())
        self.chart_drawer.refresh()

    def on_range_button(self, widget, event=None):
        button_label = widget.get_label()
        dbg_info("Button:", button_label)
        if button_label == "1D":
            # self.chart_drawer.set_date(end_date=date.today(), 1)
            # self.chart_drawer.set_drawing_type('candle')
            pass
        elif button_label == "5D":
            self.chart_drawer.set_date(end_date=date.today(), duration=7)
            self.chart_drawer.set_drawing_type('candle')
        elif button_label == "1M":
            self.chart_drawer.set_date(end_date=date.today(), duration=30)
            self.chart_drawer.set_drawing_type('candle')
        elif button_label == "3M":
            self.chart_drawer.set_date(end_date=date.today(), duration=60)
            self.chart_drawer.set_drawing_type('candle')
        elif button_label == "6M":
            self.chart_drawer.set_date(end_date=date.today(), duration=120)
            self.chart_drawer.set_drawing_type('candle')
        elif button_label == "1Y":
            self.chart_drawer.set_date(end_date=date.today(), duration=365)
            self.chart_drawer.set_drawing_type('candle')
        elif button_label == "5Y":
            self.chart_drawer.set_date(end_date=date.today(), duration=1825)
            self.chart_drawer.set_drawing_type('line')
        elif button_label == "Max":
            # FIXME I use 10 years for max
            self.chart_drawer.set_date(end_date=date.today(), duration=3650)
            self.chart_drawer.set_drawing_type('line')
        self.chart_drawer.refresh()
        # self.time_adjustment.set_value(100)

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

