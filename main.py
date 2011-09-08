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
    def __init__(self, network, room):
        super(StreamingRoom, self).__init__()
        self.daemon = True
        self.room = room
        self.network = network

    def run(self):
        stream = self.room.get_streaming()
        while True:
            print stream.get_line()

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
        gtk.main()


class TabWindow(gtk.Window):
    def destroy_event(self, widget, data=None):
        gtk.main_quit()

    def new_chat(self): # change to goto chat
        page_num = self.notebook.append_page(ChatDialog())
        self.notebook.set_current_page(page_num)

    def __init__(self):
        super(TabWindow, self).__init__()
        self.set_title("Hi")
        self.set_size_request(640, 480)
        self.set_border_width(6)

        self.connect("destroy", self.destroy_event)

        self.network = Network()
        self.rooms = RoomPicker(self.network, self)
        self.notebook = gtk.Notebook()
        self.notebook.append_page(self.rooms, gtk.Label("Rooms"))

        self.add(self.notebook)
        self.show_all()

class ChatDialog(gtk.VBox):
    def __init__(self):
        super(ChatDialog, self).__init__(False, 4)
        self.set_border_width(10)

        ok = gtk.Button("Okay")
        cancel = gtk.Button("Cancel")
        cool = gtk.Entry()

        hbox = gtk.HBox(False, 4)
        hbox.pack_start(ok, False, False)
        hbox.pack_start(cool, True, True)
        hbox.pack_start(cancel, False, False)

        text = gtk.TextView()
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(text)

        # vbox = gtk.VBox(False, 4)
        self.pack_start(sw, True, True)
        self.pack_start(hbox, False)
        self.show_all()

if __name__ == "__main__":
    # gtk.main()
    # First().run()
    TabWindow()
    gtk.main()