#!/usr/bin/env python2

import pygtk
pygtk.require("2.0")
import gtk

from pprint import pprint

from login import LoginDialog
from room_picker import RoomPicker
from chat import ChatDialog

from util import *
from config import *

import pynotify
pynotify.init("Fireplace")

def exit_menu_item(action, accel_group):
    exit_item = gtk.ImageMenuItem(gtk.STOCK_QUIT, accel_group)
    key, mod = gtk.accelerator_parse("<Control>Q")
    exit_item.add_accelerator("activate", accel_group, key, mod, gtk.ACCEL_VISIBLE)
    exit_item.connect("activate", action)
    return exit_item

# hello
class ChatController(object):
    status_icon = None
    window = None
    hidden_window = None

    def __init__(self):
        self.config = Config.load_or_create()

        if self.config.status_icon:
            self.status_icon = gtk.status_icon_new_from_stock(gtk.STOCK_OK)
            self.status_icon.connect("activate", self.on_activate_status)
            self.status_icon.connect("popup-menu", self.on_status_menu)

            agr = gtk.AccelGroup()

            menu = self.context_menu = gtk.Menu()
            exit_item = exit_menu_item(self.exit, agr)

            menu.append(exit_item)
            menu.show_all()

    def on_activate_status(self, status_icon):
        if self.hidden_window is not None:
            self.hidden_window.show()
            self.hidden_window = None
        elif self.window is not None:
            self.window.present()

    def on_status_menu(self, status_icon, button, activate_time):
        self.context_menu.popup(None, None, None, button, activate_time)

    def on_delete(self, window, event):
        if self.status_icon is not None and self.window is not None:
            self.hidden_window = window
            window.hide()
            return True

    def exit(self, *args):
        gtk.main_quit()

    def on_login(self, network, me):
        self.me = me
        self.network = network
        self.network.campfire.key = me["api_auth_token"]

        self.login_dialog.hide()
        self.window = TabWindow(self)

    def goto_chat(self, room_id, room_name):
        self.window.goto_chat(room_id, room_name)

    def start(self):
        self.login_dialog = LoginDialog(self)
        gtk.main()

    def notify(self, title, text):
        if not self.window.has_toplevel_focus():
            n = pynotify.Notification(title, text)
            n.show()

class TabWindow(gtk.Window, HasController):
    def goto_chat(self, room_id, room_name):
        if room_id in self.current_chats:
            page_id, chat = self.current_chats[room_id]
        else:
            label = gtk.Label(room_name)
            chat = ChatDialog(self.controller, room_id, label)

            # close button for tab
            image = gtk.Image()
            image.set_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)

            close_button = gtk.Button()
            close_button.set_relief(gtk.RELIEF_NONE)
            close_button.add(image)

            width, height = label.size_request()
            close_button.set_size_request(height+5, height+5)

            hbox = gtk.HBox(False, 0)
            hbox.pack_start(label)
            hbox.pack_start(close_button)
            hbox.show_all()

            page_id = self.notebook.append_page(chat, hbox)
            self.current_chats[room_id] = (page_id, chat)
            self.label_for_page.append(label)

            close_button.connect("clicked", self.on_close_chat, room_id)

        self.notebook.set_current_page(page_id)

    def on_close_chat(self, btn, room_id):
        remove_id, chat = self.current_chats[room_id]
        del self.current_chats[room_id]
        chat.shutdown()
        self.notebook.remove_page(remove_id)

        for room_id, chat_tuple in self.current_chats.iteritems():
            page_id, chat = chat_tuple
            if page_id > remove_id:
                self.current_chats[room_id] = (page_id - 1, chat)

        del self.label_for_page[remove_id]

    def on_page_change(self, notebook, page, page_num):
        label = self.label_for_page[page_num]
        self.set_title("%s - %s" % (self.config.window_title, label.get_text()))

    def build_menu(self):
        menu_bar = gtk.MenuBar()

        agr = gtk.AccelGroup()

        file_menu_item = gtk.MenuItem("_File")
        file_menu = gtk.Menu()
        exit_item = exit_menu_item(self.controller.exit, agr)
        file_menu.append(exit_item)

        file_menu_item.set_submenu(file_menu)

        options_menu_item = gtk.MenuItem("_Options")
        options_menu = gtk.Menu()

        notify_item = gtk.CheckMenuItem("Show Notifications")
        self.config.bind_to_widget("show_notifications", notify_item)

        options_menu.append(notify_item)
        options_menu_item.set_submenu(options_menu)

        menu_bar.append(file_menu_item)
        menu_bar.append(options_menu_item)
        return menu_bar

    def __init__(self, controller):
        super(TabWindow, self).__init__()
        self.controller = controller

        self.current_chats = {}
        self.label_for_page = []

        self.set_title("Chat")
        self.set_default_size(640, 400)
        # self.set_border_width(6) # where to put this?

        self.connect("delete_event", self.controller.on_delete)
        self.connect("destroy", self.controller.exit)

        self.rooms = RoomPicker(self)
        self.notebook = gtk.Notebook()
        self.notebook.connect("switch-page", self.on_page_change)

        tab_label = gtk.Label("Room List")
        self.label_for_page.append(tab_label)
        self.notebook.append_page(self.rooms, tab_label)

        vbox = gtk.VBox(False, 4)
        vbox.pack_start(self.build_menu(), False, False)
        vbox.pack_start(self.notebook, True, True)

        self.add(vbox)
        self.show_all()

if __name__ == "__main__":
    ChatController().start()