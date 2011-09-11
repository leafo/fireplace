#!/usr/bin/env python2

import pygtk
pygtk.require("2.0")
import gtk
import pango

import gobject
gobject.threads_init()

import threading
from collections import deque
from pprint import pprint

import campfire
from campfire import Campfire

from room_picker import RoomPicker

class AsyncProxy(object):
    _auto_proxy = set(['campfire'])

    def __init__(self, obj):
        self._obj = obj

    def _queue_result(self, callback, response):
        # see if we need to wrap the result...
        if response.__class__.__module__ in self._auto_proxy:
            print "wrapping result"
            response = AsyncProxy(response)
        gobject.idle_add(callback, response)

    def __str__(self):
        return "<AsyncProxy(%s)>" % str(self._obj)

    def __getattr__(self, name):
        func = getattr(self._obj, name)
        if not callable(func):
            return func

        def async_call(callback, *args):
            prox = self
            class CallbackThread(threading.Thread):
                def run(self):
                    response = func(*args)
                    if callable(callback):
                        prox._queue_result(callback, response)
            CallbackThread().start()

        return async_call


# wraps the root campfire object
class Network(AsyncProxy):
    def __init__(self):
        self.campfire = Campfire()
        super(Network, self).__init__(self.campfire)

class StreamingRoom(threading.Thread):
    def __init__(self, room, callback):
        super(StreamingRoom, self).__init__()
        self.daemon = True
        self.callback = callback
        self.room = room

    def run(self):
        stream = self.room._obj.get_streaming()
        while True:
            message = stream.get_message()
            self.callback(message)

class TabWindow(gtk.Window):
    me = None

    def destroy_event(self, widget, data=None):
        gtk.main_quit()

    def goto_chat(self, room_name):
        if room_name in self.current_chats:
            page_id, chat = self.current_chats[room_name]
        else:
            label = gtk.Label(room_name)
            chat = ChatDialog(self, room_name, label)

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
            self.current_chats[room_name] = (page_id, chat)

        self.notebook.set_current_page(page_id)

    def close_chat(self):
        pass

    def on_account(self, me):
        self.me = me["user"]
        self.ready = True

    def __init__(self):
        super(TabWindow, self).__init__()
        self.network = Network()
        self.network.api(self.on_account, "users/me")
        self.ready = False

        self.current_chats = {}

        self.set_title("Hi")
        self.set_size_request(640, 480)
        self.set_border_width(6)

        self.connect("destroy", self.destroy_event)

        self.rooms = RoomPicker(self)
        self.notebook = gtk.Notebook()
        self.notebook.append_page(self.rooms, gtk.Label("Room List"))

        self.add(self.notebook)
        self.show_all()

class ChatHistory(gtk.ScrolledWindow):
    def __init__(self, chat_dialog):
        super(ChatHistory, self).__init__()
        self.chat = chat_dialog
        self.network = chat_dialog.network

        self.text = HistoryWidget()

        self.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.add(self.text)

        self.message_queue = deque()
        self.currently_identifiying = set()

        self.ready = False

    def on_chat_dialog_ready(self):
        self.ready = True
        # re-submit the whole message queue now that we know names of users
        msgs = list(self.message_queue)
        self.message_queue.clear()
        for msg in msgs:
            self.on_message(msg)

        def write_recent(recent):
            from pprint import pprint
            for msg in recent["messages"]:
                self.on_message(msg)

        self.network.api(write_recent, "room/%d/recent" % self.chat.room.id)

    # does msg need to look up its user?
    def message_needs_identification(self, msg):
        if "user_id" in msg:
            id = msg["user_id"]
            return id is not None and id not in self.chat.user_id_to_name
        return False

    def identify_user_id(self, id):
        def identify(user):
            self.currently_identifiying.remove(id)
            self.chat.user_id_to_name[id] = user["user"]["name"]
            self.dequeue_messages()

        if id not in self.currently_identifiying:
            self.currently_identifiying.add(id)
            self.network.api(identify, "users/%d" % id)

    def dequeue_messages(self):
        while self.message_queue:
            msg = self.message_queue[0]
            if not self.message_needs_identification(msg):
                self._show_message(self.message_queue.popleft())
            else:
                return # wait to be run again

    def on_message(self, msg):
        if self.message_needs_identification(msg):
            self.identify_user_id(msg["user_id"])
            self.message_queue.append(msg)
        else:
            if not self.ready or self.message_queue:
                self.message_queue.append(msg)
            else:
                self._show_message(msg)

    def _show_message(self, msg):
        type = msg["type"]
        print "Showing", type
        try:
            func = getattr(self, "on_" + type)
        except AttributeError:
            print "Unhandled message:", type
            print msg
            return

        func(msg)

    def on_TextMessage(self, msg):
        user_name = self.chat.user_id_to_name[msg["user_id"]]
        body = msg["body"]

        is_me = msg["user_id"] == self.chat.controller.me["id"]
        self.text.write_line(user_name, body, is_me)

    def on_LeaveMessage(self, msg):
        user_name = self.chat.user_id_to_name[msg["user_id"]]
        self.text.write_status("%s left the room" % user_name)

    def on_EnterMessage(self, msg):
        user_name = self.chat.user_id_to_name[msg["user_id"]]
        self.text.write_status("%s joined the room" % user_name)

# know how to render text
class HistoryWidget(gtk.TextView):
    def __init__(self):
        super(HistoryWidget, self).__init__()

        buffer = self.get_buffer()
        buffer.create_tag("my_message", foreground="red", weight=pango.WEIGHT_HEAVY)
        buffer.create_tag("their_message", foreground="blue", weight=pango.WEIGHT_HEAVY)
        buffer.create_tag("status_message", foreground="gray", style=pango.STYLE_ITALIC)

        self.set_editable(False)
        self.set_cursor_visible(False)
        self.set_wrap_mode(gtk.WRAP_NONE)

    def scroll(self):
        a = self.get_vadjustment()
        a.value = a.upper

    def write_status(self, text):
        buffer = self.get_buffer()
        buffer.insert_with_tags_by_name(buffer.get_end_iter(),
                text + "\n", "status_message")

        self.scroll()

    # write a chat line
    def write_line(self, username, content, is_me=False):
        print username, ":", content

        buffer = self.get_buffer()
        buffer.insert_with_tags_by_name(buffer.get_end_iter(),
                "%s: " % username, "my_message" if is_me else "their_message")
        buffer.insert(buffer.get_end_iter(),
                "%s\n" % content)

        self.scroll()

class ChatDialog(gtk.VBox):
    refreshing = False
    room = None

    def create_user_list_widget(self):
        user_store = gtk.ListStore(str)
        user_list = gtk.TreeView(user_store)

        user_list.set_size_request(120, 0)

        col = gtk.TreeViewColumn("Users", gtk.CellRendererText(), text=0)
        col.set_sort_column_id(0)
        user_list.append_column(col)

        self.user_list = user_list

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(user_list)
        return sw


    def __init__(self, controller, room_name, label):
        super(ChatDialog, self).__init__(False, 4)
        self.controller = controller
        self.network = controller.network

        self.set_border_width(6)

        self.send_button = gtk.Button("Send")
        self.send_button.connect("clicked", self.on_click_send)

        self.entry = gtk.Entry()
        self.entry.connect("activate", self.on_send)

        self.entry.set_sensitive(False)
        self.send_button.set_sensitive(False)

        hbox = gtk.HBox(False, 4)
        hbox.pack_start(self.entry, True, True)
        hbox.pack_start(self.send_button, False, False)

        self.history = ChatHistory(self)

        user_list = self.create_user_list_widget()
        pane = gtk.HPaned()
        pane.pack1(self.history, True)
        pane.pack2(user_list, False)

        self.pack_start(pane, True, True)
        self.pack_start(hbox, False)
        self.show_all()

        self.network.join(self.on_join, room_name)

        self.user_id_to_name = {}


    def refresh(self):
        if self.refreshing: return
        self.refreshing = True
        self.room.get_users(self.on_refresh)

    def on_refresh(self, users):
        store = self.user_list.get_model()
        store.clear()

        for user in users:
            self.user_id_to_name[user["id"]] = user["name"]
            store.append([user["name"]])

        self.refreshing = False
        self.history.on_chat_dialog_ready()

    def on_click_send(self, button):
        self.on_send(self.entry)

    def on_send(self, entry):
        text = entry.get_text()
        if not text: return
        print "sending:", text
        self.room.speak(None, text)
        entry.set_text("")

    def on_join(self, room):
        self.room = room
        self.entry.set_sensitive(True)
        self.send_button.set_sensitive(True)

        self.refresh()
        self.stream = StreamingRoom(self.room, self.history.on_message)
        self.stream.start()

if __name__ == "__main__":
    # gtk.main()
    # First().run()
    TabWindow()
    gtk.main()