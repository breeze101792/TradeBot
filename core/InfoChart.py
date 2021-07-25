import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
#---------------------------
from graphic.Drawer import *

class InfoChart:
    def __init__(self):
        ##############################################
        ## preset set
        ##############################################
        super().__init__()
        self.current_product = None

        ##############################################
        ## preset set
        ##############################################
        # self.base_grid = Gtk.Box()
        self.base_grid = Gtk.Grid()
        self.base_grid.set_column_homogeneous(True)
        # self.base_grid.set_column_spacing(2)
        # self.base_grid.set_row_spacing(2)

        self.product_name = Gtk.Label(label="Market")
        # self.product_name.set_halign(Gtk.Align.END)
        # self.product_name.set_halign(Gtk.Align.FILL)
        self.base_grid.attach(self.product_name, 0, 0, 1, 1)
        # self.base_grid.add(self.product_name)

        self.chart_drawer = SingleDraw()
        # self.chart_drawer.set_layout(1)
        # self.chart_drawer.set_drawing_type("line")
        # self.chart_drawer.set_axis_mode(0)

        self.drawer_canvas = self.chart_drawer.get_canvas()
        # self.drawer_canvas.set_hexpand(True)
        # self.drawer_canvas.set_vexpand(False)
        # self.drawer_canvas.set_halign(Gtk.Align.END)
        # self.drawer_canvas.set_halign(Gtk.Align.FILL)
        self.drawer_canvas.set_size_request(80, 60)
        self.base_grid.attach(self.drawer_canvas, 1, 0, 1, 1)



    def refresh(self):
        self.product_name.set_label(self.current_product.name + "(" + self.current_product.code + ")")
        self.chart_drawer.refresh()

    def set_product(self, product):
        self.current_product = product
        self.chart_drawer.set_product(self.current_product)
    def get_product(self):
        return self.current_product

    def get_product_code(self):
        if self.current_product is None:
            return str("0")
        return self.current_product.code


    def get_main_layer(self):
        return self.base_grid
