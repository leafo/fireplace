
import gtk
import pango

from collections import deque
from network import StreamingRoom

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
        # print "Showing", type
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

    def on_KickMessage(self, msg):
        user_name = self.chat.user_id_to_name[msg["user_id"]]
        self.text.write_status("%s was kicked from the room" % user_name)

    def on_TimestampMessage(self, msg):
        pass

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
        buffer = self.get_buffer()
        buffer.insert_with_tags_by_name(buffer.get_end_iter(),
                "%s: " % username, "my_message" if is_me else "their_message")
        buffer.insert(buffer.get_end_iter(),
                "%s\n" % content)

        self.scroll()

class ChatDialog(gtk.VBox):
    stream = None
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

    def __init__(self, controller, room_id, label):
        super(ChatDialog, self).__init__(False, 4)
        self.label = label
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

        self.network.join_by_id(self.on_join, room_id)

        self.user_id_to_name = {}

    def shutdown(self):
        if self.stream is not None:
            self.stream.queue_finish()
        self.room.leave(None)

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
        self.label.set_text(room.name)

        self.entry.set_sensitive(True)
        self.send_button.set_sensitive(True)

        self.refresh()
        self.stream = StreamingRoom(self.room, self.history.on_message)
        self.stream.start()
