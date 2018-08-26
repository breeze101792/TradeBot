#!/usr/bin/env python3
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
    def refresh(self):
        self.ax.cla()
        self.ax.patch.set_alpha(0)
        self.ax.set_title(self.title)
    def draw(self):
        self.fig.canvas.draw()
    def get_canvas(self):
        return self.canvas
    def set_point(self, point):
        # point = [[1,2,3],[4,5,6]]
        self.ax.plot(point[0], point[1], self.color[0] + "-")
    def clear(self):
        self.ax.cla()

class paper:
    def __init__(self, unit_xy = (10, 10), title = ""):
        self.color = ["r","b","g","c","m","y","k","w"]
        self.data = None
        # self.fig = plt.figure()

        self.fig = Figure(figsize = unit_xy, dpi=80)
        self.fig.patch.set_facecolor('none')

        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        self.title = title
        self.resetpaper()

    def resetpaper(self):
        self.ax.cla()
        self.ax.patch.set_alpha(0)
        self.ax.set_title(self.title)
        # self.ax.set_xlim(-0.02,1.02)
        # self.ax.set_ylim(-0.02,1.02)
        # self.ax.grid(True)
    def expend_lim(self, v = 0.02):
        self.ax.set_xlim(self.ax.get_xlim()[0]-v,self.ax.get_xlim()[1]+v)
        self.ax.set_ylim(self.ax.get_ylim()[0]-v,self.ax.get_ylim()[1]+v)
    def draw(self):
        self.fig.canvas.draw()
        

        # self.fig.canvas.draw()
        # plt.draw()
        # plt.show()

    def draw_2d_point(self, dataset, class_middle, shape = '.'):
        data_point = dataset[0]
        data_y = dataset[1]
        tmp_point = []
        class_list = []
        for point, y in zip(data_point, data_y):
            if y not in class_list:
                class_list.append(y)
                tmp_point.append([[point[0]],[point[1]]])
            else:
                tmp_point[class_list.index(y)][0].append(point[0])
                tmp_point[class_list.index(y)][1].append(point[1])

        for idx in range(len(class_list)):
            self.ax.plot(tmp_point[idx][0], tmp_point[idx][1], self.color[class_middle.index(class_list[idx])] + shape)
    #draw (point,color, shape)
    def draw_2d_area(self, dataset):
        self.ax.pcolor(dataset[0][0], dataset[0][1], dataset[1], cmap='RdBu')
        # x = linspace(0, map.urcrnrx, data.shape[1])
        # y = linspace(0, map.urcrnry, data.shape[0])
        # xx, yy = meshgrid(x, y)





        # a1 = np.linspace(0,100,40)
        # a2 = np.linspace(30,100,40)
        #
        # x = np.arange(0, len(a1), 1)
        #
        # self.ax.fill_between(x, 0, a1, facecolor='green')
        # self.ax.fill_between(x, a1, a2, facecolor='red')
        #
        # self.ax.fill_between([1],0,[0],facecolor='green')

    #TODO
    def draw_2d_line(self, slope, bias):
        pass
        # if self.weights == 1:
        #     x = np.linspace(plt.xlim()[0], plt.xlim()[1], 2)
        #     y = np.linspace(plt.ylim()[0], plt.ylim()[1], 2)
        #     if self.weights[1] == 0:
        #         y = [self.weights[0]/self.weights[2],self.weights[0]/self.weights[2]]
        #     elif self.weights[2] == 0:
        #         x = [self.weights[0]/self.weights[1],self.weights[0]/self.weights[1]]
        #     else:
        #         #x = [0,self.weights[0]/self.weights[1]]
        #         print("draw")
        #         if -self.weights[1]/self.weights[2] > 1:
        #             print(" > ")
        #             x = (self.weights[0] - self.weights[2] * x) / self.weights[1]
        #         else:
        #             y = (self.weights[0] - self.weights[1] * x) / self.weights[2]
        #     plt.plot(x, y ,"k--")
        # else:
        #     for idx, each_weights in enumerate(self.weights):
        #         print(each_weights)
        #         x = np.linspace(plt.xlim()[0], plt.xlim()[1], 2)
        #         y = np.linspace(plt.ylim()[0], plt.ylim()[1], 2)
        #         if each_weights[1] == 0:
        #             y = [each_weights[0]/each_weights[2],each_weights[0]/each_weights[2]]
        #         elif each_weights[2] == 0:
        #             x = [each_weights[0]/each_weights[1],each_weights[0]/each_weights[1]]
        #         else:
        #             print("normal")
        #             #x = [0,self.weights[0]/self.weights[1]]
        #             if abs(-each_weights[1]/each_weights[2]) > 1:
        #                 x = (each_weights[0] - each_weights[2] * y) / each_weights[1]
        #             else:
        #                 y = (each_weights[0] - each_weights[1] * x) / each_weights[2]
        #         plt.plot(x, y ,color[idx] + "--")

    def __draw_3d(self):
        pass
    def draw_net(self, net, i_len, j_len):
        # print(net, i_len, j_len)
        tmp_x = []
        tmp_y = []
        h_x = []
        h_y = []
        v_x = []
        v_y = []
        for j in range(j_len):
            v_x = []
            v_y = []
            for i in range(i_len):
                v_x.append(net[i][j][0])
                v_y.append(net[i][j][1])
            self.ax.plot(v_x, v_y, 'b-')
        for i in range(i_len):
            h_x = []
            h_y = []
            for j in range(j_len):
                h_x.append(net[i][j][0])
                h_y.append(net[i][j][1])
            tmp_x.append(h_x)
            tmp_y.append(h_y)
            self.ax.plot(h_x, h_y, 'b-')
        # self.ax.plot(tmp_x, tmp_y, 'b.')

class MainClass():
    def __init__(self, canvas):
        self.window = Gtk.Window()
        self.window.set_default_size(800, 500)
        self.boxvertical = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.add(self.boxvertical)

        # drawing fig
        self.box = Gtk.Box()
        self.boxvertical.pack_start(self.box, True, True, 0)
        self.box.pack_start(canvas, True, True, 0)
        # self.fig.canvas.draw()



def main():
    # print("drawing function")
    # data = dp('/home/shaowu/code/neural_network/dataset/2Ccircle1.txt')
    # data.open_file()
    # p = paper()
    # p.draw_2d_point(data.get_data(),data.get_class_middle())
    # p.draw_2d_area(data.get_data())
    # p.draw()


    # mc = MainClass(p.canvas)

    # mc.window.connect("delete-event", Gtk.main_quit)
    # mc.window.show_all()
    # Gtk.main()
    pass

if __name__ == '__main__':
    main()
