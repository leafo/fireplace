
import gtk

class RoomPicker(gtk.VBox):
    refresh_text = "Refresh"
    refreshing_text = "Refreshing..."

    def __init__(self, network, controller):
        super(RoomPicker, self).__init__(False, 4)
        # self.set_title("Room Picker")
        # self.set_size_request(350, 250)

        self.controller = controller
        self.network = network
        self.set_border_width(6)

        self.store = gtk.ListStore(str, str)
        tree_view = gtk.TreeView(self.store)
        tree_view.connect("row-activated", self.on_activate)
        tree_view.set_rules_hint(True)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.create_columns(tree_view)
        sw.add(tree_view)

        # the button bar
        button_box = gtk.HBox(False)
        join_button = gtk.Button("Join")
        self.refresh_button = gtk.Button(self.refresh_text)

        button_box.pack_start(self.refresh_button, False)
        button_box.pack_start(join_button, False)

        self.refresh_button.connect("clicked", self.on_click_refresh)

        align = gtk.Alignment(1.0, 0,0,0)
        align.add(button_box)

        # vbox = gtk.VBox(False, 4)
        self.pack_start(sw, True, True)
        self.pack_start(align, False)

        self.on_click_refresh(None)
        self.show_all()
        # self.add(vbox)

    def on_click_refresh(self, btn):
        self.refresh_button.set_sensitive(False)
        self.refresh_button.set_label(self.refreshing_text)

        self.network.api(self.fill_rooms, "rooms")

    def fill_rooms(self, response):
        print repr(response)
        self.store.clear()
        for room in response["rooms"]:
            self.store.append([room["name"], room["topic"]])

        self.refresh_button.set_sensitive(True)
        self.refresh_button.set_label(self.refresh_text)

    def on_activate(self, widget, row, col):
        # print "activate row:", row, "col:", col
        print self.store[row][0]
        self.controller.new_chat()

    def create_columns(self, tree_view):
        col = gtk.TreeViewColumn("Name", gtk.CellRendererText(), text=0)
        col.set_sort_column_id(0)
        tree_view.append_column(col)

        col = gtk.TreeViewColumn("Topic", gtk.CellRendererText(), text=1)
        col.set_sort_column_id(1)
        tree_view.append_column(col)


