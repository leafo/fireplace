#!/usr/bin/env python2

import pygtk
pygtk.require("2.0")
import gtk

import gobject
gobject.threads_init()

import threading

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

class First(object):
    def hello(self, widget, data=None):
        print "hello world"

    def delete_event(self, widget, data=None):
        print "delete_event"
        return False

    def destroy_event(self, widget, data=None):
        print "destroy_event"
        gtk.main_quit()

    def on_key_release(self, widget, event):
        print "got key release"

    def dump_event(self, widget):
        text = widget.get_text()
        print "sending:", text
        self.room.speak(None, text)
        widget.set_text("")

    def __init__(self):
        # self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)

        # self.window.connect("delete_event", self.delete_event)
        # self.window.connect("destroy", self.destroy_event)

        # self.window.set_border_width(10)

        # self.input = gtk.Entry()
        # # self.input.add_events(gtk.gdk.KEY_RELEASE_MASK) # what does thisr do?
        # # self.input.connect("key-release-event", self.on_key_release)
        # self.input.connect("activate", self.dump_event)
        # self.input.set_sensitive(False)

        # self.window.add(self.input)
        # self.input.show()
        # self.window.show()

        self.network = Network()
        self.network.join(self.on_connect, "Room 1")

        # rooms = RoomPicker(self.network)
        # ChatDialog()

    def on_connect(self, room):
        self.room = room
        # self.input.set_sensitive(True)

    def run(self):
        tk.main()


class TabWindow(gtk.Window):
    def destroy_event(self, widget, data=None):
        gtk.main_quit()

    def goto_chat(self, room_name):
        if room_name in self.current_chats:
            page_id, chat = self.current_chats[room_name]
        else:
            chat = ChatDialog(self, room_name)
            page_id = self.notebook.append_page(chat, gtk.Label(room_name))
            self.current_chats[room_name] = (page_id, chat)

        self.notebook.set_current_page(page_id)

    def close_chat(self):
        pass

    def __init__(self):
        super(TabWindow, self).__init__()

        self.current_chats = {}

        self.set_title("Hi")
        self.set_size_request(640, 480)
        self.set_border_width(6)

        self.connect("destroy", self.destroy_event)

        self.network = Network()
        self.rooms = RoomPicker(self)
        self.notebook = gtk.Notebook()
        self.notebook.append_page(self.rooms, gtk.Label("Room List"))

        self.add(self.notebook)
        self.show_all()

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

    def __init__(self, controller, room_name):
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

        self.history = gtk.TextView()
        self.history.set_editable(False)
        self.history.set_cursor_visible(False)
        self.history.set_wrap_mode(gtk.WRAP_NONE)

        scrolled_history = gtk.ScrolledWindow()
        scrolled_history.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        scrolled_history.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        scrolled_history.add(self.history)

        user_list = self.create_user_list_widget()
        pane = gtk.HPaned()
        pane.pack1(scrolled_history, True)
        pane.pack2(user_list, False)

        self.pack_start(pane, True, True)
        self.pack_start(hbox, False)
        self.show_all()

        self.network.join(self.on_join, room_name)

        # messages that couldn't be displayed yet because we don't have user names
        self.undisplayed_messages = []
        self.user_id_to_name = {}


    # we also need to refresh the chat history (for d/c)
    def refresh(self):
        if self.refreshing: return
        self.refreshing = True
        self.room.get_users(self.on_refresh)

    def on_refresh(self, users):
        store = self.user_list.get_model()
        store.clear()
        # TODO: need to handle messages coming from users that aren't in the room
        self.user_id_to_name = {}
        for user in users:
            self.user_id_to_name[user["id"]] = user["name"]
            store.append([user["name"]])

        # write unsent messages
        for user_id, msg in self.undisplayed_messages:
            if user_id in self.user_id_to_name:
                self.add_line(self.user_id_to_name[user_id], msg)

        del self.undisplayed_messages[:]
        self.refreshing = False

    def on_click_send(self, button):
        self.on_send(self.entry)

    def on_send(self, entry):
        text = entry.get_text()
        if not text: return
        print "sending:", text
        self.room.speak(None, text)
        entry.set_text("")

    def on_message(self, msg):
        print "msg:", msg
        user_id = msg["user_id"]
        if user_id in self.user_id_to_name:
            self.add_line(self.user_id_to_name[user_id], msg["body"])
        else:
            self.undisplayed_messages.append((user_id, msg["body"]))
            self.refresh()

    def on_join(self, room):
        self.room = room
        self.entry.set_sensitive(True)
        self.send_button.set_sensitive(True)

        self.refresh()
        self.stream = StreamingRoom(self.room, self.on_message)
        self.stream.start()

    # add a line to the history
    def add_line(self, username, content):
        print username, ":", content
        buffer = self.history.get_buffer()
        buffer.insert(buffer.get_end_iter(), "%s: %s\n" % (username, content))

if __name__ == "__main__":
    # gtk.main()
    # First().run()
    TabWindow()
    gtk.main()