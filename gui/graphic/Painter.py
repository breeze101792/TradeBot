#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')

from gi.repository import Gtk
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas
from gi.repository.GdkPixbuf import Pixbuf
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

class Painter:
    def __init__(self, unit_xy = (10, 10), title = ""):
        self.color = ["r","b","g","c","m","y","k","w"]
        self.data = None
        # self.fig = plt.figure()

        self.fig = Figure(figsize = unit_xy, dpi=80)
        self.fig.patch.set_facecolor('none')

        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        self.title = title
        self.refresh()
    # action
    def refresh(self):
        self.ax.cla()
        self.ax.patch.set_alpha(0)
        self.ax.set_title(self.title)
    def draw(self):
        self.fig.canvas.draw()
    def clear(self):
        self.ax.cla()
    # attr
    def get_canvas(self):
        return self.canvas
    def draw_2d_line(self, data_point):
        # point = [[1,2,3],[4,5,6]]
        self.ax.plot(data_point[0], data_point[1], self.color[0] + "-")
    def draw_box(self):
        spread = np.random.rand(50) * 100
        center = np.ones(25) * 50
        flier_high = np.random.rand(10) * 100 + 100
        flier_low = np.random.rand(10) * -100
        data = np.concatenate((spread, center, flier_high, flier_low), 0)
        self.ax.boxplot(data)

def painter_main():
    win = Gtk.Window()
    win.connect("delete-event", Gtk.main_quit)
    win.set_default_size(400, 300)
    win.set_title("Embedding in GTK")

    sw = Gtk.ScrolledWindow()
    win.add(sw)
    # A scrolled window border goes outside the scrollbars and viewport
    sw.set_border_width(10)

    # --------------------------------------
    # fig = Figure(figsize=(5, 4), dpi=100)
    # ax = fig.add_subplot()
    # t = np.arange(0.0, 3.0, 0.01)
    # s = np.sin(2*np.pi*t)
    # ax.plot(t, s)

    # canvas = FigureCanvas(fig)  # a Gtk.DrawingArea
    # canvas.set_size_request(800, 600)
    painter = Painter()
    canvas = painter.get_canvas()
    painter.draw_box()

    # --------------------------------------
    sw.add(canvas)

    win.show_all()
    Gtk.main()



if __name__ == '__main__':
    painter_main()
