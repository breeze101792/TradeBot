import numpy as np
import mplfinance as mpf
import pandas as pd
# ------------------------------------
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

# from matplotlib.backends.backend_gtk3agg import (
#     FigureCanvasGTK3Agg as FigureCanvas)
from matplotlib.backends.backend_gtk3cairo import (
    FigureCanvasGTK3Cairo as FigureCanvas)
from matplotlib.figure import Figure
import matplotlib
matplotlib.use("GTK3Cairo")
from datetime import datetime


class Drawer:
    def __init__(self, unit_xy = (10, 10), title = ""):
        # self.color = ["r","b","g","c","m","y","k","w"]
        self.product= None
        self.pdata = None

        self.ax1 = None
        self.ax2 = None
        self.ax3 = None

        self.fig = mpf.figure(style='yahoo',figsize=(9,8))

        self.canvas = FigureCanvas(self.fig)
        self.canvas.set_size_request(800, 600)


    # action
    def refresh(self):
        if self.ax1 is not None:
            self.ax1.remove()
        if self.ax2 is not None:
            self.ax2.remove()
        if self.ax3 is not None:
            self.ax3.remove()
        # self.fig.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=None, hspace=0.5)
        self.ax1 = self.fig.add_subplot(3,1,(1,2))
        self.ax2 = self.fig.add_subplot(3,1,3,sharex=self.ax1)
        # self.pdata.head()
        dbg_warning("Remove Specific days restriction")


        # -------------------------------------
        # start = datetime.datetime(2021, 6, 1)
        # end = datetime.datetime(2021, 7, 1)
        # index = pd.date_range(start, end)

        # pdata_window = self.pdata.bdate_range(start, end)
        # pdata_window = self.pdata["2021-07"]
        # pdata_window = self.pdata["2021-07"]
        # pdata_window = self.pdata['2021-06-01' :'2021-07-20']

        pdata_window = self.pdata.loc['2021-06-01' :'2021-07-20']

        # pdata_window = self.pdata['2021-07-01' :'2021-07-20']
        # pdata_window = self.pdata['2021-01-01' :'2021-07-20']
        # pdata_window = self.pdata[(self.pdata.Timestamp >= datetime(2021, 6, 1)) & (df.Timestamp <= datetime(2021, 7, 20))]
        # -------------------------------------
        # print(pdata_window.head())
        # print(pdata_window.isnull())

        # self.pdata['2021-06-01' :'2021-07-20'].head()
        # mpf.plot(self.pdata['2021-06-01' :'2021-07-20'],type='candle',ax=self.ax1,volume=self.ax2)
        mpf.plot(pdata_window.astype(float), type='candle',ax=self.ax1,volume=self.ax2)
        # mpf.plot(self.pdata,type='candle',ax=self.ax1,volume=self.ax2)
        self.canvas.draw()
    def clear(self):
        pass
        # self.ax.cla()
    # attr
    def get_canvas(self):
        return self.canvas
    def set_product(self, product):
        self.product = product
        self.pdata = product.data.pdata
        # self.pdata.head()


import sys
sys.path.insert(0, '../')
from market.Market import *
from utility.common import *
def drawer_main():
    win = Gtk.Window()
    win.connect("delete-event", Gtk.main_quit)
    win.set_default_size(400, 300)
    win.set_title("Embedding in GTK")

    sw = Gtk.ScrolledWindow()
    win.add(sw)
    # A scrolled window border goes outside the scrollbars and viewport
    sw.set_border_width(10)

    # --------------------------------------
    tw_mkt = Market()
    # product_code = "1569"
    product_code = "2330"

    product_ins = tw_mkt.get_product(product_code.__str__())
    drawer = Drawer()
    # print(product_ins.data.pdata)
    drawer.set_product(product_ins)
    canvas = drawer.get_canvas()
    drawer.draw()

    # --------------------------------------
    sw.add(canvas)

    win.show_all()
    Gtk.main()

def drawer_example():
    win = Gtk.Window()
    win.connect("delete-event", Gtk.main_quit)
    win.set_default_size(400, 300)
    win.set_title("Embedding in GTK")

    sw = Gtk.ScrolledWindow()
    win.add(sw)
    # A scrolled window border goes outside the scrollbars and viewport
    sw.set_border_width(10)

    # --------------------------------------
    # https://github.com/matplotlib/mplfinance/blob/master/examples/external_axes.ipynb
    df = pd.DataFrame([
        ['2021-02-01',70161939,595.00,612.00,587.00,611.00],
        ['2021-02-02',80724207,629.00,638.00,622.00,632.00],
        ['2021-02-03',59763227,638.00,642.00,630.00,630.00],
        ['2021-02-04',47547873,626.00,632.00,620.00,627.00],
        ['2021-02-05',57350831,638.00,641.00,631.00,632.00],
        ['2021-02-17',115578402,663.00,668.00,660.00,663.00],
        ['2021-02-18',54520341,664.00,665.00,656.00,660.00],
        ['2021-02-19',51651844,656.00,657.00,647.00,652.00],
        ['2021-02-22',39512078,660.00,662.00,650.00,650.00],
        ['2021-02-23',52868029,641.00,643.00,633.00,641.00],
        ['2021-02-24',80010637,627.00,636.00,625.00,625.00],
        ['2021-02-25',45279276,636.00,636.00,628.00,635.00],
        ['2021-02-26',137933162,611.00,618.00,606.00,606.00],
    ], columns=['Date', 'Volume', 'Open', 'High', 'Low', 'Close'])
    df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
    df.set_index('Date', inplace=True)

    # mpf.plot(df, type='candle', title='2330')
    fig = mpf.figure(style='yahoo',figsize=(9,8))
    # fig.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=None, hspace=0.5)
    ax1 = fig.add_subplot(3,1,(1,2))
    ax2 = fig.add_subplot(3,1,3,sharex=ax1)
    mpf.plot(df,type='candle',ax=ax1,volume=ax2)


    # fig = Figure(figsize=(5, 4), dpi=100)
    # ax = fig.add_subplot()
    # t = np.arange(0.0, 3.0, 0.01)
    # s = np.sin(2*np.pi*t)
    # ax.plot(t, s)

    canvas = FigureCanvas(fig)  # a Gtk.DrawingArea
    canvas.set_size_request(800, 600)
    # drawer = Drawer()
    # canvas = drawer.get_canvas()
    # drawer.draw_box()

    # --------------------------------------
    sw.add(canvas)

    win.show_all()
    Gtk.main()
def drawer_ui_example():
    win = Gtk.Window()
    win.connect("delete-event", Gtk.main_quit)
    win.set_default_size(400, 300)
    win.set_title("Embedding in GTK")

    sw = Gtk.ScrolledWindow()
    win.add(sw)
    # A scrolled window border goes outside the scrollbars and viewport
    sw.set_border_width(10)

    # --------------------------------------
    # https://github.com/matplotlib/mplfinance/blob/master/examples/external_axes.ipynb
    df = pd.DataFrame([
        ['2021-02-01',70161939,595.00,612.00,587.00,611.00],
        ['2021-02-02',80724207,629.00,638.00,622.00,632.00],
        ['2021-02-03',59763227,638.00,642.00,630.00,630.00],
        ['2021-02-04',47547873,626.00,632.00,620.00,627.00],
        ['2021-02-05',57350831,638.00,641.00,631.00,632.00],
        ['2021-02-17',115578402,663.00,668.00,660.00,663.00],
        ['2021-02-18',54520341,664.00,665.00,656.00,660.00],
        ['2021-02-19',51651844,656.00,657.00,647.00,652.00],
        ['2021-02-22',39512078,660.00,662.00,650.00,650.00],
        ['2021-02-23',52868029,641.00,643.00,633.00,641.00],
        ['2021-02-24',80010637,627.00,636.00,625.00,625.00],
        ['2021-02-25',45279276,636.00,636.00,628.00,635.00],
        ['2021-02-26',137933162,611.00,618.00,606.00,606.00],
    ], columns=['Date', 'Volume', 'Open', 'High', 'Low', 'Close'])
    df['Date'] = pd.to_datetime(df['Date'], format='%Y-%m-%d')
    df.set_index('Date', inplace=True)

    # mpf.plot(df, type='candle', title='2330')
    fig = mpf.figure(style='yahoo',figsize=(9,8))
    # fig.subplots_adjust(left=None, bottom=None, right=None, top=None, wspace=None, hspace=0.5)
    ax1 = fig.add_subplot(3,1,(1,2))
    ax2 = fig.add_subplot(3,1,3,sharex=ax1)
    mpf.plot(df,type='candle',ax=ax1,volume=ax2)


    # fig = Figure(figsize=(5, 4), dpi=100)
    # ax = fig.add_subplot()
    # t = np.arange(0.0, 3.0, 0.01)
    # s = np.sin(2*np.pi*t)
    # ax.plot(t, s)

    canvas = FigureCanvas(fig)  # a Gtk.DrawingArea
    # canvas.set_size_request(800, 600)
    # drawer = Drawer()
    # canvas = drawer.get_canvas()
    # drawer.draw_box()

    # --------------------------------------
    hbox = Gtk.Box(spacing=6)
    sw.add(hbox)
    hbox.pack_start(canvas, True, True, 0)

    button = Gtk.Button.new_with_label("Click Me")
    # button.connect("clicked", self.on_click_me_clicked)
    hbox.pack_start(button, True, True, 0)


    # sw.add(canvas)

    win.show_all()
    Gtk.main()


if __name__ == '__main__':
    # drawer_example()
    # drawer_main()
    drawer_ui_example()

