import threading
import time

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib
from graphic.Painter import Painter


def app_main():
    win = Gtk.Window(default_height=50, default_width=300)
    win.connect("delete-event", Gtk.main_quit)

    progress = Gtk.ProgressBar(show_text=True)
    win.add(progress)

    def update_progess(i):
        progress.pulse()
        progress.set_text(str(i))
        return False

    def example_target():
        for i in range(50):
            GLib.idle_add(update_progess, i)
            time.sleep(0.2)

    win.show_all()

    thread = threading.Thread(target=example_target)
    thread.daemon = True
    thread.start()

class SideBarInfoBox:
    def __init__(self):
        self.side_bar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.side_bar_box.set_hexpand(False)

        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.search_entry = Gtk.SearchEntry()
        # search_entry.set_input_hints("test")
        self.search_entry.set_text("2454")

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
        print("Refresh ")
        self.stock_name_label.set_text(self.search_entry.get_text())
    def set_search_callback(self, cb_func):
        self.search_entry.connect("stop-search", cb_func)
        self.search_entry.connect("search-changed", cb_func)
        self.search_button.connect("button-press-event", cb_func)
    # attr
    def get_stock_name(self):
        return self.stock_name_label.get_text()


class MainChartBox:
    def __init__(self):
        self._var_stock_name = str()
        self.box_main_chart = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        label_title = Gtk.Label(label="Graphic Chart")
        self.box_main_chart.pack_start(label_title, False, False, 0)

        self.chart_painter = Painter()
        self.box_main_chart.pack_start(self.chart_painter.get_canvas(), True, True, 4)

    def refresh(self):
        print("Refresh Chart " + self._var_stock_name)
        self.chart_painter.draw_box()
        
    def get_main_layer(self):
        return self.box_main_chart
    # attr
    @property
    def var_stock_name(self):
        return self._var_stock_name
    @var_stock_name.setter
    def var_stock_name(self, value):
        print("Setter " + value)
        self._var_stock_name = value
        

class UIManager(Gtk.Window):
    
    def __init__(self):
        Gtk.Window.__init__(self, title="Investor")

        self.set_default_size(800, 500)

        # Program Layout
        menu_main_group = Gtk.ActionGroup("MainFrame")

        self.add_file_menu_actions(menu_main_group)
        self.add_edit_menu_actions(menu_main_group)
        self.add_choices_menu_actions(menu_main_group)

        uimanager = self.create_ui_manager()
        uimanager.insert_action_group(menu_main_group)

        menubar = uimanager.get_widget("/MenuBar")

        basebox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(basebox)
        
        basebox.pack_start(menubar, False, False, 0)

        toolbar = uimanager.get_widget("/ToolBar")
        basebox.pack_start(toolbar, False, False, 0)

        # main frame
        main_frame = Gtk.Box()
        basebox.pack_start(main_frame, True, True, 0)

        self.side_bar_info_box = SideBarInfoBox()
        self.side_bar_info_box.set_search_callback(self.on_search_action)
        main_frame.pack_start(self.side_bar_info_box.get_main_layer(), False, False, 0)

        self.main_chart_box = MainChartBox()
        main_frame.pack_start(self.main_chart_box.get_main_layer(), True, True, 0)

    def ui_start(self):
        self.connect("destroy", Gtk.main_quit)
        self.show_all()
        Gtk.main()

    # UI creation
    def create_ui_manager(self):
        ui_info = None
        with open('graphic/UISettings.xml') as f:
            ui_info = f.read()
            f.closed
        uimanager = Gtk.UIManager()

        # Throws exception if something went wrong
        uimanager.add_ui_from_string(ui_info)

        # Add the accelerator group to the toplevel window
        accelgroup = uimanager.get_accel_group()
        self.add_accel_group(accelgroup)
        return uimanager

    def add_file_menu_actions(self, action_group):
        action_filemenu = Gtk.Action("FileMenu", "File", None, None)
        action_group.add_action(action_filemenu)

        action_filenewmenu = Gtk.Action("FileNew", None, None, Gtk.STOCK_NEW)
        action_group.add_action(action_filenewmenu)

        action_new = Gtk.Action("FileNewStandard", "_New",
            "Create a new file", Gtk.STOCK_NEW)
        action_new.connect("activate", self.on_menu_file_new_generic)
        action_group.add_action_with_accel(action_new, None)

        action_group.add_actions([
            ("FileNewFoo", None, "New Foo", None, "Create new foo",
             self.on_menu_file_new_generic),
            ("FileNewGoo", None, "_New Goo", None, "Create new goo",
             self.on_menu_file_new_generic),
        ])

        action_filequit = Gtk.Action("FileQuit", None, None, Gtk.STOCK_QUIT)
        action_filequit.connect("activate", self.on_menu_file_quit)
        action_group.add_action(action_filequit)

    def add_edit_menu_actions(self, action_group):
        action_group.add_actions([
            ("EditMenu", None, "Edit"),
            ("EditCopy", Gtk.STOCK_COPY, None, None, None,
             self.on_menu_others),
            ("EditPaste", Gtk.STOCK_PASTE, None, None, None,
             self.on_menu_others),
            ("EditSomething", None, "Something", "<control><alt>S", None,
             self.on_menu_others)
        ])

    def add_choices_menu_actions(self, action_group):
        action_group.add_action(Gtk.Action("ChoicesMenu", "Choices", None,
            None))

        action_group.add_radio_actions([
            ("ChoiceOne", None, "One", None, None, 1),
            ("ChoiceTwo", None, "Two", None, None, 2)
        ], 1, self.on_menu_choices_changed)

        three = Gtk.ToggleAction("ChoiceThree", "Three", None, None)
        three.connect("toggled", self.on_menu_choices_toggled)
        action_group.add_action(three)
    # call back function
    def on_menu_file_new_generic(self, widget):
        print("A File|New menu item was selected.")

    def on_menu_file_quit(self, widget):
        Gtk.main_quit()

    def on_menu_others(self, widget):
        print("Menu item " + widget.get_name() + " was selected")

    def on_menu_choices_changed(self, widget, current):
        print(current.get_name() + " was selected.")

    def on_menu_choices_toggled(self, widget):
        if widget.get_active():
            print(widget.get_name() + " activated")
        else:
            print(widget.get_name() + " deactivated")
    def on_search_action(self, widget, event=None):
        print("On Search Action")
        self.side_bar_info_box.refresh()
        self.main_chart_box.var_stock_name = self.side_bar_info_box.get_stock_name()
        self.main_chart_box.refresh()

if __name__ == "__main__":
    window = UIManager()        
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    Gtk.main()
    # win = UIManager()
    # win.connect("destroy", Gtk.main_quit)
    # win.show_all()
    # Gtk.main()

    # pass
    # Calling GObject.threads_init() is not needed for PyGObject 3.10.2+
    # GObject.threads_init()

    # PyApp()
    # Gtk.main()
