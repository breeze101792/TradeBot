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
from core.MainChart import *
from core.TabManager import *
from utility.debug import *

class UIManager(Gtk.Window):
    def __init__(self):
        self.current_product = None
        self.mkt = Market()

        super().__init__(title="Investor")
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
        main_frame.pack_start(self.side_bar_info_box.get_main_layer(), False, False, 5)

        # self.main_chart_box = MainChart()
        # main_frame.pack_start(self.main_chart_box.get_main_layer(), True, True, 0)

        self.tab_manager = TabManager()
        self.tab_manager.set_event_cb(self.on_product_callback)
        main_frame.pack_start(self.tab_manager.get_main_layer(), True, True, 0)

        self.initialization()

    def initialization(self):
        self.current_product = self.mkt.get_product("2330") 
        # self.current_product.data.dump()

        self.side_bar_info_box.set_product(self.current_product)
        self.side_bar_info_box.refresh()

        self.tab_manager.set_product(self.current_product)
        self.tab_manager.refresh()

    def ui_start(self):
        self.connect("destroy", Gtk.main_quit)
        self.show_all()
        Gtk.main()

    # UI creation
    def create_ui_manager(self):
        ui_info = None
        with open('core/UISettings.xml') as f:
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
        dbg_info("A File|New menu item was selected.")

    def on_menu_file_quit(self, widget):
        Gtk.main_quit()

    def on_menu_others(self, widget):
        dbg_info("Menu item " + widget.get_name() + " was selected")

    def on_menu_choices_changed(self, widget, current):
        dbg_info(current.get_name() + " was selected.")

    def on_menu_choices_toggled(self, widget):
        if widget.get_active():
            dbg_info(widget.get_name() + " activated")
        else:
            dbg_info(widget.get_name() + " deactivated")
    def on_product_callback(self, args, event=None):
        self.current_product = args
        # self.current_product.data.dump()

        self.side_bar_info_box.set_product(self.current_product)
        self.side_bar_info_box.refresh()

        self.tab_manager.set_product(self.current_product)
        self.tab_manager.refresh()
    def on_search_action(self, widget, event=None):
        search_str = self.side_bar_info_box.get_search_entry()
        dbg_info("On Search Action %s, Event %s", (search_str, event))

        if search_str == "":
            return

        product = self.mkt.get_product(search_str)
        # self.current_product.data.dump()
        self.on_product_callback(product, None)

        # self.side_bar_info_box.set_product(self.current_product)
        # self.side_bar_info_box.refresh()

        # self.tab_manager.set_product(self.current_product)
        # self.tab_manager.refresh()

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

# import threading
# import time
# def app_main():
#     win = Gtk.Window(default_height=50, default_width=300)
#     win.connect("delete-event", Gtk.main_quit)

#     progress = Gtk.ProgressBar(show_text=True)
#     win.add(progress)

#     def update_progess(i):
#         progress.pulse()
#         progress.set_text(str(i))
#         return False

#     def example_target():
#         for i in range(50):
#             GLib.idle_add(update_progess, i)
#             time.sleep(0.2)

#     win.show_all()

#     thread = threading.Thread(target=example_target)
#     thread.daemon = True
#     thread.start()

