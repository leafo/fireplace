#!/usr/bin/env python2

import pygtk
pygtk.require("2.0")
import gtk

from pprint import pprint

from login import LoginDialog
from room_picker import RoomPicker
from chat import ChatDialog

class HasController(object):
    @property
    def me(self):
        return self.controller.me

    @property
    def network(self):
        return self.controller.network

# hello
class ChatController(object):
    def on_login(self, network, me):
        self.me = me
        self.network = network
        self.network.campfire.key = me["api_auth_token"]

        self.login_dialog.hide()
        TabWindow(self)

    def start(self):
        self.login_dialog = LoginDialog(self)
        gtk.main()

# move controller out of here
class TabWindow(gtk.Window, HasController):
    def on_destroy(self, widget, data=None):
        gtk.main_quit()

    def goto_chat(self, room_id, room_name):
        if room_id in self.current_chats:
            page_id, chat = self.current_chats[room_id]
        else:
            label = gtk.Label(room_name)
            chat = ChatDialog(self, room_id, label)

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
        self.set_size_request(640, 200)
        self.set_border_width(6)

        self.connect("destroy", self.on_destroy)

        self.rooms = RoomPicker(self)
        self.notebook = gtk.Notebook()
        self.notebook.append_page(self.rooms, gtk.Label("Room List"))

        self.add(self.notebook)
        self.show_all()

if __name__ == "__main__":
    ChatController().start()