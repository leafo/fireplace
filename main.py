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
            exit_item = gtk.ImageMenuItem(gtk.STOCK_QUIT, agr)
            key, mod = gtk.accelerator_parse("<Control>Q")
            exit_item.add_accelerator("activate", agr, key, mod, gtk.ACCEL_VISIBLE)
            exit_item.connect("activate", self.on_destroy)

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

    def on_destroy(self, window):
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

    def __init__(self, controller):
        super(TabWindow, self).__init__()
        self.controller = controller

        self.current_chats = {}

        self.set_title("Chat")
        self.set_default_size(640, 400)
        self.set_border_width(6)

        self.connect("delete_event", self.controller.on_delete)
        self.connect("destroy", self.controller.on_destroy)

        self.rooms = RoomPicker(self)
        self.notebook = gtk.Notebook()
        self.notebook.append_page(self.rooms, gtk.Label("Room List"))

        self.add(self.notebook)
        self.show_all()

if __name__ == "__main__":
    ChatController().start()